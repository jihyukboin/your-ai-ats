"""Corporate identity, disclosures and occupational standards from Korean public APIs."""
import io
import os
import re
import time
import xml.etree.ElementTree as ET
from datetime import date, timedelta
from zipfile import ZipFile

FSC = "https://www.data.go.kr/data/15043184/openapi.do"
NCS = "https://www.data.go.kr/data/15128213/openapi.do"
DART = "https://opendart.fss.or.kr"
_directory = (0, {})


def secret(name):
    if not (value := os.getenv(name)):
        raise ValueError(f"{name} 설정 필요")
    return value


def normalized(name):
    return re.sub(r"주식회사|\(주\)|㈜|\s+", "", name).casefold()


async def public_rows(client, path, params):
    response = await client.get("https://apis.data.go.kr/" + path, params=params)
    response.raise_for_status()
    payload = response.json()
    data = payload.get("response", payload)
    code = str(data["header"]["resultCode"])
    if code == "03":
        return []
    if code not in ("00", "0", "0000", "000"):
        raise ValueError("공공데이터 응답 코드 " + code[:8])
    items = (data.get("body") or {}).get("items") or []
    if isinstance(items, dict):
        items = items.get("item", [])
    return [items] if isinstance(items, dict) else items


async def corporate_identity(client, name):
    rows = await public_rows(client, "1160100/service/GetCorpBasicInfoService_V2/getCorpOutline_V2",
                             dict(ServiceKey=secret("DATA_GO_KR_API_KEY"), resultType="json",
                                  corpNm=name, pageNo=1, numOfRows=100))
    matches = [r for r in rows if normalized(r.get("corpNm", "")) == normalized(name)]
    if len({r.get("crno") for r in matches}) != 1:
        return []
    row = max(matches, key=lambda r: r.get("basDt", ""))
    return [{k: row.get(k) for k in ("corpNm", "crno", "enpRprFnm", "enpEstbDt", "basDt")}]


async def disclosures(client, name):
    global _directory
    key = secret("DART_API_KEY")
    if time.monotonic() >= _directory[0]:
        response = await client.get(DART + "/api/corpCode.xml", params={"crtfc_key": key})
        response.raise_for_status()
        with ZipFile(io.BytesIO(response.content)) as archive:
            root = ET.fromstring(archive.read("CORPCODE.xml"))
        names = {}
        for item in root.findall("list"):
            names.setdefault(normalized(item.findtext("corp_name", "")), []).append(item.findtext("corp_code"))
        _directory = time.monotonic() + 86400, names
    codes = _directory[1].get(normalized(name), [])
    if len(codes) != 1:
        return []
    response = await client.get(DART + "/api/company.json", params={"crtfc_key": key, "corp_code": codes[0]})
    response.raise_for_status()
    row = response.json()
    if row.get("status") != "000":
        raise ValueError("DART 응답 코드 " + str(row.get("status", ""))[:8])
    evidence = {k: row.get(k) for k in ("corp_name", "corp_code", "ceo_nm", "induty_code", "est_dt", "hm_url")}
    report = await client.get(DART + "/api/list.json", params={
        "crtfc_key": key, "corp_code": codes[0], "pblntf_detail_ty": "A001", "last_reprt_at": "Y",
        "bgn_de": (date.today() - timedelta(days=730)).strftime("%Y%m%d"), "page_count": 1})
    report.raise_for_status()
    recent = report.json().get("list", [])
    if recent:
        filing = recent[0]
        evidence.update(report=filing["report_nm"], filed=filing["rcept_dt"],
                        url="https://dart.fss.or.kr/dsaf001/main.do?rcpNo=" + filing["rcept_no"])
    return [evidence]


async def competencies(client, role):
    if not role:
        return []
    rows = await public_rows(client, "B490007/hrdkapi/NCS007",
                             dict(serviceKey=secret("DATA_GO_KR_API_KEY"), pageNo=1, numOfRows=10,
                                  LVL=1, SWRD=role, SNUM=1, ENUM=10))
    return [{k: row.get(k) for k in ("NCS_SUBD_CDNM", "DUTY_DEF", "COMPE_UNIT_NAME", "COMPE_UNIT_DEF")}
            for row in rows]
