#!/usr/bin/env python3
"""Tencent Hunyuan 3D API 3.0 client with project-gate integration."""

from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import hmac
import json
import mimetypes
import os
import re
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


CLIENT_VERSION = "1.0"
ENDPOINT = "ai3d.tencentcloudapi.com"
SERVICE = "ai3d"
API_VERSION = "2025-05-13"
DEFAULT_REGION = "ap-guangzhou"
CONTENT_TYPE = "application/json; charset=utf-8"

SUBMIT_TO_QUERY = {
    "SubmitHunyuanTo3DProJob": "QueryHunyuanTo3DProJob",
    "SubmitHunyuanTo3DRapidJob": "QueryHunyuanTo3DRapidJob",
    "SubmitTextureTo3DJob": "DescribeTextureTo3DJob",
    "SubmitReduceFaceJob": "DescribeReduceFaceJob",
    "SubmitHunyuan3DPartJob": "QueryHunyuan3DPartJob",
    "SubmitHunyuanTo3DUVJob": "DescribeHunyuanTo3DUVJob",
    "SubmitHunyuanTo3DMotionJob": "DescribeHunyuanTo3DMotionJob",
    "SubmitAutoRiggingJob": "DescribeAutoRiggingJob",
    "SubmitProfileTo3DJob": "DescribeProfileTo3DJob",
}
QUERY_ACTIONS = set(SUBMIT_TO_QUERY.values())
ALLOWED_ACTIONS = set(SUBMIT_TO_QUERY) | QUERY_ACTIONS | {"Convert3DFormat"}
SAFE_DOWNLOAD_SUFFIXES = (".tencentcos.cn", ".myqcloud.com")


class ClientError(RuntimeError):
    pass


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def atomic_write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(path.name + ".tmp")
    temp_path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temp_path, path)


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ClientError(f"无法读取JSON：{path}：{exc}") from exc
    if not isinstance(value, dict):
        raise ClientError(f"JSON根必须是对象：{path}")
    return value


def strip_url_secret(value: str) -> str:
    parsed = urllib.parse.urlsplit(value)
    if not parsed.scheme or not parsed.netloc:
        return "LOCAL_OR_INVALID"
    return urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", ""))


def sanitize_params(value: Any) -> Any:
    if isinstance(value, dict):
        result: dict[str, Any] = {}
        for key, item in value.items():
            lower = key.lower()
            if "base64" in lower:
                result[key] = f"<omitted:{len(str(item))} chars>"
            elif lower.endswith("url") and isinstance(item, str):
                result[key] = strip_url_secret(item)
            else:
                result[key] = sanitize_params(item)
        return result
    if isinstance(value, list):
        return [sanitize_params(item) for item in value]
    return value


def _get_case_insensitive(row: dict[str, str], *names: str) -> str:
    wanted = {re.sub(r"[^a-z0-9]", "", name.lower()) for name in names}
    for key, value in row.items():
        normalized = re.sub(r"[^a-z0-9]", "", (key or "").lower())
        if normalized in wanted and value:
            return value.strip()
    return ""


def load_credentials(credential_csv: str | None) -> dict[str, str]:
    candidates: list[Path] = []
    if credential_csv:
        candidates.append(Path(credential_csv))
    elif os.environ.get("HUNYUAN3D_CREDENTIAL_CSV"):
        candidates.append(Path(os.environ["HUNYUAN3D_CREDENTIAL_CSV"]))

    secret_id = os.environ.get("TENCENTCLOUD_SECRET_ID", "").strip()
    secret_key = os.environ.get("TENCENTCLOUD_SECRET_KEY", "").strip()
    session_token = os.environ.get("TENCENTCLOUD_SESSION_TOKEN", "").strip()
    if secret_id and secret_key and not credential_csv:
        return {
            "secret_id": secret_id,
            "secret_key": secret_key,
            "session_token": session_token,
            "source": "environment",
        }

    default_csv = Path.home() / "Desktop" / "新建子用户信息.csv"
    if not candidates and default_csv.is_file():
        candidates.append(default_csv)

    for path in candidates:
        if not path.is_file():
            raise ClientError(f"凭据CSV不存在：{path}")
        try:
            with path.open("r", encoding="utf-8-sig", newline="") as handle:
                rows = list(csv.DictReader(handle))
        except (OSError, csv.Error) as exc:
            raise ClientError(f"凭据CSV读取失败：{path}：{exc}") from exc
        for row in rows:
            row_secret_id = _get_case_insensitive(row, "SecretId", "Secret ID", "CAM SecretId")
            row_secret_key = _get_case_insensitive(row, "SecretKey", "Secret Key", "CAM SecretKey")
            row_token = _get_case_insensitive(row, "Token", "SessionToken", "Session Token")
            if row_secret_id and row_secret_key:
                return {
                    "secret_id": row_secret_id,
                    "secret_key": row_secret_key,
                    "session_token": row_token,
                    "source": str(path),
                }
        raise ClientError(f"凭据CSV中未找到同一行的SecretId/SecretKey：{path}")

    raise ClientError(
        "未找到腾讯云CAM凭据；设置TENCENTCLOUD_SECRET_ID/TENCENTCLOUD_SECRET_KEY，"
        "或传入--credential-csv。"
    )


def _sign(key: bytes, message: str) -> bytes:
    return hmac.new(key, message.encode("utf-8"), hashlib.sha256).digest()


def build_headers(
    action: str,
    payload: bytes,
    region: str,
    credentials: dict[str, str],
    timestamp: int | None = None,
) -> dict[str, str]:
    timestamp = int(time.time()) if timestamp is None else timestamp
    date = datetime.fromtimestamp(timestamp, timezone.utc).strftime("%Y-%m-%d")
    canonical_headers = (
        f"content-type:{CONTENT_TYPE}\n"
        f"host:{ENDPOINT}\n"
        f"x-tc-action:{action.lower()}\n"
    )
    signed_headers = "content-type;host;x-tc-action"
    hashed_payload = hashlib.sha256(payload).hexdigest()
    canonical_request = (
        "POST\n/\n\n"
        + canonical_headers
        + "\n"
        + signed_headers
        + "\n"
        + hashed_payload
    )
    credential_scope = f"{date}/{SERVICE}/tc3_request"
    string_to_sign = (
        "TC3-HMAC-SHA256\n"
        + str(timestamp)
        + "\n"
        + credential_scope
        + "\n"
        + hashlib.sha256(canonical_request.encode("utf-8")).hexdigest()
    )
    secret_date = _sign(("TC3" + credentials["secret_key"]).encode("utf-8"), date)
    secret_service = _sign(secret_date, SERVICE)
    secret_signing = _sign(secret_service, "tc3_request")
    signature = hmac.new(secret_signing, string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()
    authorization = (
        "TC3-HMAC-SHA256 "
        f"Credential={credentials['secret_id']}/{credential_scope}, "
        f"SignedHeaders={signed_headers}, Signature={signature}"
    )
    headers = {
        "Authorization": authorization,
        "Content-Type": CONTENT_TYPE,
        "Host": ENDPOINT,
        "X-TC-Action": action,
        "X-TC-Timestamp": str(timestamp),
        "X-TC-Version": API_VERSION,
        "X-TC-Region": region,
    }
    if credentials.get("session_token"):
        headers["X-TC-Token"] = credentials["session_token"]
    return headers


def api_call(
    action: str,
    params: dict[str, Any],
    region: str,
    credentials: dict[str, str],
    timeout: int = 60,
) -> dict[str, Any]:
    if action not in ALLOWED_ACTIONS:
        raise ClientError(f"动作不在官方白名单：{action}")
    payload = json.dumps(params, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    request = urllib.request.Request(
        f"https://{ENDPOINT}/",
        data=payload,
        headers=build_headers(action, payload, region, credentials),
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read()
    except urllib.error.HTTPError as exc:
        body = exc.read(8192)
        message = body.decode("utf-8", errors="replace")
        raise ClientError(f"腾讯云HTTP错误 {exc.code}：{message[:1000]}") from exc
    except urllib.error.URLError as exc:
        raise ClientError(f"腾讯云网络错误：{exc.reason}") from exc
    try:
        result = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ClientError("腾讯云返回了不可解析的JSON") from exc
    response_value = result.get("Response", {})
    if not isinstance(response_value, dict):
        raise ClientError("腾讯云响应缺少Response对象")
    error = response_value.get("Error")
    if isinstance(error, dict):
        code = str(error.get("Code", "Unknown"))
        message = str(error.get("Message", ""))
        raise ClientError(f"腾讯云API错误 {code}：{message}")
    return response_value


def validate_result_url(url: str) -> urllib.parse.SplitResult:
    parsed = urllib.parse.urlsplit(url)
    host = (parsed.hostname or "").lower()
    if parsed.scheme != "https" or not any(host.endswith(suffix) for suffix in SAFE_DOWNLOAD_SUFFIXES):
        raise ClientError(f"拒绝下载非腾讯COS HTTPS地址：{strip_url_secret(url)}")
    return parsed


def download_one(url: str, destination: Path) -> dict[str, Any]:
    validate_result_url(url)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temp_path = destination.with_name(destination.name + ".part")
    digest = hashlib.sha256()
    total = 0
    try:
        with urllib.request.urlopen(url, timeout=180) as response, temp_path.open("wb") as handle:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                handle.write(chunk)
                digest.update(chunk)
                total += len(chunk)
        os.replace(temp_path, destination)
    except Exception:
        if temp_path.exists():
            temp_path.unlink()
        raise
    return {"path": str(destination), "bytes": total, "sha256": digest.hexdigest()}


def _suffix_for_url(url: str, fallback: str) -> str:
    suffix = Path(urllib.parse.urlsplit(url).path).suffix.lower()
    if not suffix or len(suffix) > 10:
        suffix = fallback
    return suffix


def download_results(files: list[dict[str, Any]], output_dir: Path) -> list[dict[str, Any]]:
    outputs: list[dict[str, Any]] = []
    for index, item in enumerate(files, start=1):
        file_type = re.sub(r"[^A-Za-z0-9_-]", "", str(item.get("Type", "FILE"))) or "FILE"
        for field, kind, fallback in (
            ("Url", "model", ".bin"),
            ("PreviewImageUrl", "preview", ".png"),
        ):
            url = item.get(field)
            if not isinstance(url, str) or not url:
                continue
            suffix = _suffix_for_url(url, fallback)
            destination = output_dir / f"result_{index:02d}_{file_type.lower()}_{kind}{suffix}"
            record = download_one(url, destination)
            record.update({"kind": kind, "type": file_type, "source": strip_url_secret(url)})
            outputs.append(record)
    return outputs


def response_summary(response: dict[str, Any]) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    for key in (
        "JobId",
        "RequestId",
        "Status",
        "ErrorCode",
        "ErrorMessage",
        "ResultCreditConsumed",
        "ResultCreditDetails",
    ):
        if key in response:
            summary[key] = response[key]
    files = response.get("ResultFile3Ds")
    if isinstance(files, list):
        summary["ResultFile3Ds"] = [
            {
                "Type": item.get("Type"),
                "Url": strip_url_secret(str(item.get("Url", ""))),
                "PreviewImageUrl": strip_url_secret(str(item.get("PreviewImageUrl", ""))),
            }
            for item in files
            if isinstance(item, dict)
        ]
    return summary


def update_gate(gate_path: Path | None, state: dict[str, Any]) -> None:
    if gate_path is None:
        return
    gate = load_json(gate_path)
    execution = gate.setdefault("execution", {})
    status = str(state.get("status", "UNKNOWN"))
    gate_state = {
        "SUBMITTED": "SUBMITTED",
        "WAIT": "WAITING",
        "RUN": "WAITING",
        "DONE": "RETURNED",
        "FAIL": "BLOCKED",
        "ERROR": "BLOCKED",
    }.get(status, gate.get("state", "REQUIRED"))
    gate["state"] = gate_state
    gate["updated_at"] = utc_now()
    if status == "SUBMITTED" and state.get("job_id") and execution.get("job_id") != state.get("job_id"):
        execution["attempt_count"] = int(execution.get("attempt_count", 0)) + 1
    execution.update(
        {
            "status": status,
            "job_id": state.get("job_id", ""),
            "request_id": state.get("request_id", ""),
            "client_state_file": state.get("state_file", ""),
            "result_credit_consumed": state.get("result_credit_consumed"),
            "outputs": state.get("outputs", []),
            "error": state.get("error", ""),
        }
    )
    atomic_write_json(gate_path, gate)


def validate_gate_for_submit(gate: dict[str, Any]) -> dict[str, Any]:
    if gate.get("state") != "REQUIRED":
        raise ClientError(f"资产闸门不是REQUIRED：{gate.get('state')}")
    decision = gate.get("decision")
    execution = gate.get("execution")
    request = gate.get("request")
    if not isinstance(decision, dict) or not isinstance(execution, dict) or not isinstance(request, dict):
        raise ClientError("资产闸门缺少decision/request/execution对象")
    if decision.get("needs_new_3d_asset") is not True:
        raise ClientError("资产闸门未确认需要新3D资产")
    if decision.get("semantic_lock") != "LOCKED":
        raise ClientError("资产语义尚未LOCKED")
    if decision.get("existing_asset_search") != "MISSING":
        raise ClientError("资产库检索结果必须是MISSING")
    if decision.get("copyright_decision") not in {"ALLOW_SELF", "ALLOW_LICENSED"}:
        raise ClientError("版权闸门未放行")
    if not str(request.get("asset_id") or "").strip():
        raise ClientError("资产闸门request.asset_id不能为空")
    if not str(request.get("output_dir") or "").strip():
        raise ClientError("资产闸门request.output_dir不能为空")
    if not execution.get("auto_submit_authorized", False):
        raise ClientError("资产闸门未授权自动提交")
    attempt_count = int(execution.get("attempt_count", 0))
    if attempt_count >= 2:
        raise ClientError("资产闸门已达到两次生成上限")
    if attempt_count == 1 and not str(execution.get("retry_evidence") or "").strip():
        raise ClientError("第二次生成前必须填写retry_evidence")
    return request


def execute_async(
    action: str,
    query_action: str,
    params: dict[str, Any],
    output_dir: Path,
    region: str,
    credentials: dict[str, str],
    poll_seconds: int,
    timeout_seconds: int,
    submit_only: bool = False,
    gate_path: Path | None = None,
    resume_job_id: str | None = None,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    state_path = output_dir / "hunyuan3d_job.json"
    state: dict[str, Any] = {
        "schema_version": 1,
        "client_version": CLIENT_VERSION,
        "endpoint": ENDPOINT,
        "api_version": API_VERSION,
        "region": region,
        "action": action,
        "query_action": query_action,
        "submitted_at": utc_now(),
        "updated_at": utc_now(),
        "status": "SUBMITTED",
        "job_id": resume_job_id or "",
        "request_id": "",
        "credential_source": credentials["source"],
        "request": sanitize_params(params),
        "poll_count": 0,
        "result_credit_consumed": None,
        "result_credit_details": None,
        "outputs": [],
        "error": "",
        "state_file": str(state_path),
    }
    try:
        if not resume_job_id:
            response = api_call(action, params, region, credentials)
            state["job_id"] = str(response.get("JobId", ""))
            state["request_id"] = str(response.get("RequestId", ""))
            if not state["job_id"]:
                raise ClientError("提交响应缺少JobId")
            state["updated_at"] = utc_now()
            atomic_write_json(state_path, state)
            update_gate(gate_path, state)
            if submit_only:
                return state

        deadline = time.monotonic() + timeout_seconds
        while True:
            response = api_call(query_action, {"JobId": state["job_id"]}, region, credentials)
            status = str(response.get("Status", "UNKNOWN"))
            state.update(
                {
                    "status": status,
                    "request_id": str(response.get("RequestId", state["request_id"])),
                    "updated_at": utc_now(),
                    "poll_count": int(state["poll_count"]) + 1,
                    "result_credit_consumed": response.get("ResultCreditConsumed"),
                    "result_credit_details": response.get("ResultCreditDetails"),
                }
            )
            if status == "DONE":
                files = response.get("ResultFile3Ds") or []
                if not isinstance(files, list):
                    raise ClientError("DONE响应的ResultFile3Ds不是数组")
                state["outputs"] = download_results(files, output_dir)
                atomic_write_json(state_path, state)
                update_gate(gate_path, state)
                return state
            if status == "FAIL":
                state["error"] = f"{response.get('ErrorCode', '')}: {response.get('ErrorMessage', '')}".strip()
                atomic_write_json(state_path, state)
                update_gate(gate_path, state)
                raise ClientError(f"混元3D任务失败：{state['error']}")
            if status not in {"WAIT", "RUN"}:
                raise ClientError(f"未知任务状态：{status}")
            atomic_write_json(state_path, state)
            update_gate(gate_path, state)
            if time.monotonic() >= deadline:
                raise ClientError(f"轮询超时；可用resume继续：JobId={state['job_id']}")
            time.sleep(poll_seconds)
    except Exception as exc:
        state["status"] = "ERROR" if state.get("status") not in {"FAIL", "DONE"} else state["status"]
        state["error"] = str(exc)
        state["updated_at"] = utc_now()
        atomic_write_json(state_path, state)
        update_gate(gate_path, state)
        raise


def encode_image_file(path: Path) -> str:
    if not path.is_file():
        raise ClientError(f"输入图片不存在：{path}")
    if path.stat().st_size > 6 * 1024 * 1024:
        raise ClientError("输入图片超过6MiB的Base64源文件限制")
    mime, _ = mimetypes.guess_type(path.name)
    if mime not in {"image/jpeg", "image/png", "image/webp"}:
        raise ClientError("输入图片格式仅支持jpg/png/webp")
    return base64.b64encode(path.read_bytes()).decode("ascii")


def build_generation_request(values: dict[str, Any]) -> tuple[str, str, dict[str, Any]]:
    edition = str(values.get("edition", "rapid")).lower()
    if edition not in {"rapid", "pro"}:
        raise ClientError("edition必须是rapid或pro")
    prompt = str(values.get("prompt") or "").strip()
    image_url = str(values.get("image_url") or "").strip()
    image_file = str(values.get("image_file") or "").strip()
    provided = sum(bool(item) for item in (prompt, image_url, image_file))
    if provided != 1:
        raise ClientError("Prompt、ImageUrl、ImageFile必须且只能提供一个")
    prompt_limit = 200 if edition == "rapid" else 1024
    if prompt and len(prompt) > prompt_limit:
        raise ClientError(f"{edition}提示词超过{prompt_limit}字符：{len(prompt)}")
    params: dict[str, Any] = {}
    if prompt:
        params["Prompt"] = prompt
    elif image_url:
        validate_result_url(image_url)
        params["ImageUrl"] = image_url
    else:
        params["ImageBase64"] = encode_image_file(Path(image_file))

    if edition == "rapid":
        action = "SubmitHunyuanTo3DRapidJob"
        query = "QueryHunyuanTo3DRapidJob"
        if values.get("result_format"):
            params["ResultFormat"] = str(values["result_format"]).upper()
        if values.get("enable_pbr"):
            params["EnablePBR"] = True
        if values.get("enable_geometry"):
            params["EnableGeometry"] = True
    else:
        action = "SubmitHunyuanTo3DProJob"
        query = "QueryHunyuanTo3DProJob"
        model = str(values.get("model") or "3.1")
        generate_type = str(values.get("generate_type") or "Normal")
        if model not in {"3.0", "3.1"}:
            raise ClientError("专业版Model必须是3.0或3.1")
        if generate_type not in {"Normal", "LowPoly", "Geometry", "Sketch"}:
            raise ClientError("GenerateType无效")
        if model == "3.1" and generate_type == "LowPoly":
            raise ClientError("官方接口不支持Model 3.1搭配LowPoly")
        params.update({"Model": model, "GenerateType": generate_type})
        if values.get("enable_pbr"):
            params["EnablePBR"] = True
        if values.get("face_count") is not None:
            face_count = int(values["face_count"])
            if not 3000 <= face_count <= 1_500_000:
                raise ClientError("FaceCount必须在3000到1500000之间")
            params["FaceCount"] = face_count
        if values.get("result_format"):
            params["ResultFormat"] = str(values["result_format"]).upper()
        if values.get("polygon_type"):
            params["PolygonType"] = str(values["polygon_type"])
    return action, query, params


def common_values(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "edition": args.edition,
        "prompt": args.prompt,
        "image_url": args.image_url,
        "image_file": args.image_file,
        "model": args.model,
        "generate_type": args.generate_type,
        "result_format": args.result_format,
        "enable_pbr": args.enable_pbr,
        "enable_geometry": args.enable_geometry,
        "face_count": args.face_count,
        "polygon_type": args.polygon_type,
    }


def run_generation(args: argparse.Namespace) -> dict[str, Any]:
    action, query, params = build_generation_request(common_values(args))
    credentials = load_credentials(args.credential_csv)
    return execute_async(
        action,
        query,
        params,
        Path(args.output_dir).resolve(),
        args.region,
        credentials,
        args.poll_seconds,
        args.timeout_seconds,
        submit_only=args.submit_only,
    )


def run_gate(args: argparse.Namespace) -> dict[str, Any]:
    gate_path = Path(args.gate_file).resolve()
    gate = load_json(gate_path)
    request = validate_gate_for_submit(gate)
    quality = str(request.get("quality_target", "previs")).lower()
    edition = str(request.get("edition", "auto")).lower()
    if edition == "auto":
        edition = "rapid" if quality in {"previs", "blockout", "proxy"} else "pro"
    values = dict(request)
    values["edition"] = edition
    action, query, params = build_generation_request(values)
    output_dir = str(request["output_dir"]).strip()
    credentials = load_credentials(args.credential_csv)
    return execute_async(
        action,
        query,
        params,
        Path(output_dir).resolve(),
        args.region,
        credentials,
        args.poll_seconds,
        args.timeout_seconds,
        gate_path=gate_path,
    )


def resume_job(args: argparse.Namespace) -> dict[str, Any]:
    edition = args.edition.lower()
    query = "QueryHunyuanTo3DProJob" if edition == "pro" else "QueryHunyuanTo3DRapidJob"
    action = "SubmitHunyuanTo3DProJob" if edition == "pro" else "SubmitHunyuanTo3DRapidJob"
    credentials = load_credentials(args.credential_csv)
    return execute_async(
        action,
        query,
        {},
        Path(args.output_dir).resolve(),
        args.region,
        credentials,
        args.poll_seconds,
        args.timeout_seconds,
        gate_path=Path(args.gate_file).resolve() if args.gate_file else None,
        resume_job_id=args.job_id,
    )


def invoke_action(args: argparse.Namespace) -> dict[str, Any]:
    params = load_json(Path(args.params_file).resolve())
    credentials = load_credentials(args.credential_csv)
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    if args.action in SUBMIT_TO_QUERY and args.wait:
        return execute_async(
            args.action,
            SUBMIT_TO_QUERY[args.action],
            params,
            output_dir,
            args.region,
            credentials,
            args.poll_seconds,
            args.timeout_seconds,
        )
    response = api_call(args.action, params, args.region, credentials)
    summary = response_summary(response)
    files = response.get("ResultFile3Ds") or []
    outputs = download_results(files, output_dir) if isinstance(files, list) else []
    result = {
        "schema_version": 1,
        "client_version": CLIENT_VERSION,
        "action": args.action,
        "updated_at": utc_now(),
        "response": summary,
        "outputs": outputs,
    }
    atomic_write_json(output_dir / "hunyuan3d_action.json", result)
    return result


def self_test() -> dict[str, Any]:
    with tempfile.TemporaryDirectory() as temp:
        temp_path = Path(temp)
        csv_path = temp_path / "credentials.csv"
        csv_path.write_text(
            "Username,Password,SecretId,SecretKey,LoginURL\n"
            "tester,unused,EXAMPLE_SECRET_ID_NOT_VALID,0123456789abcdef0123456789abcdef,https://example.invalid\n",
            encoding="utf-8",
        )
        credentials = load_credentials(str(csv_path))
        payload = b'{"Prompt":"test"}'
        headers = build_headers(
            "SubmitHunyuanTo3DRapidJob",
            payload,
            DEFAULT_REGION,
            credentials,
            timestamp=1_700_000_000,
        )
        expected_credential_prefix = (
            f"TC3-HMAC-SHA256 Credential={credentials['secret_id']}/"
        )
        if not headers["Authorization"].startswith(expected_credential_prefix):
            raise ClientError("TC3签名自检失败")
        action, query, params = build_generation_request(
            {"edition": "rapid", "prompt": "一个测试立方体"}
        )
        if action not in SUBMIT_TO_QUERY or SUBMIT_TO_QUERY[action] != query or params["Prompt"] == "":
            raise ClientError("生成路由自检失败")
        if "?" in strip_url_secret("https://x.cos.ap-guangzhou.tencentcos.cn/a.zip?q-sign=secret"):
            raise ClientError("URL脱敏自检失败")
        gate = {
            "state": "REQUIRED",
            "decision": {
                "needs_new_3d_asset": True,
                "semantic_lock": "LOCKED",
                "existing_asset_search": "MISSING",
                "copyright_decision": "ALLOW_SELF",
            },
            "request": {"asset_id": "TEST", "output_dir": str(temp_path)},
            "execution": {"auto_submit_authorized": True, "attempt_count": 0},
        }
        validate_gate_for_submit(gate)
    return {"status": "PASS", "client_version": CLIENT_VERSION, "tests": 5}


def add_network_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--credential-csv")
    parser.add_argument("--region", default=os.environ.get("TENCENTCLOUD_REGION", DEFAULT_REGION))
    parser.add_argument("--poll-seconds", type=int, default=10)
    parser.add_argument("--timeout-seconds", type=int, default=1200)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="腾讯混元生3D API 3.0客户端")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("self-test", help="运行离线安全自检")
    credentials_parser = sub.add_parser("credentials", help="只验证凭据解析，不联网")
    credentials_parser.add_argument("--credential-csv")

    run_parser = sub.add_parser("run", help="提交并完成专业版或极速版生成")
    run_parser.add_argument("--edition", choices=("rapid", "pro"), required=True)
    inputs = run_parser.add_mutually_exclusive_group(required=True)
    inputs.add_argument("--prompt")
    inputs.add_argument("--image-url")
    inputs.add_argument("--image-file")
    run_parser.add_argument("--output-dir", required=True)
    run_parser.add_argument("--model", default="3.1")
    run_parser.add_argument("--generate-type", default="Normal")
    run_parser.add_argument("--result-format")
    run_parser.add_argument("--enable-pbr", action="store_true")
    run_parser.add_argument("--enable-geometry", action="store_true")
    run_parser.add_argument("--face-count", type=int)
    run_parser.add_argument("--polygon-type")
    run_parser.add_argument("--submit-only", action="store_true")
    add_network_options(run_parser)

    gate_parser = sub.add_parser("gate-run", help="读取REQUIRED资产闸门并自动完成生成")
    gate_parser.add_argument("--gate-file", required=True)
    add_network_options(gate_parser)

    resume_parser = sub.add_parser("resume", help="继续轮询并下载已有任务")
    resume_parser.add_argument("--edition", choices=("rapid", "pro"), required=True)
    resume_parser.add_argument("--job-id", required=True)
    resume_parser.add_argument("--output-dir", required=True)
    resume_parser.add_argument("--gate-file")
    add_network_options(resume_parser)

    invoke_parser = sub.add_parser("invoke", help="调用官方白名单动作，参数从JSON读取")
    invoke_parser.add_argument("--action", choices=sorted(ALLOWED_ACTIONS), required=True)
    invoke_parser.add_argument("--params-file", required=True)
    invoke_parser.add_argument("--output-dir", required=True)
    invoke_parser.add_argument("--wait", action="store_true")
    add_network_options(invoke_parser)
    return parser


def validate_runtime_options(args: argparse.Namespace) -> None:
    if hasattr(args, "poll_seconds") and not 2 <= args.poll_seconds <= 120:
        raise ClientError("poll-seconds必须在2到120之间")
    if hasattr(args, "timeout_seconds") and not 30 <= args.timeout_seconds <= 7200:
        raise ClientError("timeout-seconds必须在30到7200之间")


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        validate_runtime_options(args)
        if args.command == "self-test":
            result = self_test()
        elif args.command == "credentials":
            credentials = load_credentials(args.credential_csv)
            result = {
                "status": "PASS",
                "source": credentials["source"],
                "secret_id_length": len(credentials["secret_id"]),
                "secret_key_length": len(credentials["secret_key"]),
                "session_token_present": bool(credentials.get("session_token")),
            }
        elif args.command == "run":
            result = run_generation(args)
        elif args.command == "gate-run":
            result = run_gate(args)
        elif args.command == "resume":
            result = resume_job(args)
        elif args.command == "invoke":
            result = invoke_action(args)
        else:
            raise ClientError(f"未知命令：{args.command}")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except ClientError as exc:
        print(json.dumps({"status": "ERROR", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
