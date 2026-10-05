"""Bounded offline replay of the normalized DNS cache contract in SCHEMA.md."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import ipaddress
import json
import re
import sys

MAX_BYTES = 1024 * 1024
MAX_EVENTS = 256
MAX_ENTRIES = 256
TYPES = {"A", "AAAA", "CNAME"}
DOC_V4 = tuple(ipaddress.ip_network(n) for n in
               ("192.0.2.0/24", "198.51.100.0/24", "203.0.113.0/24"))
DOC_V6 = ipaddress.ip_network("2001:db8::/32")


class LabError(ValueError):
    """Invalid or unsupported scenario; no partial timeline is emitted."""


def fields(value: object, required: set[str], optional: set[str] = frozenset()) -> dict:
    if not isinstance(value, dict) or not required <= value.keys() or value.keys() - required - optional:
        raise LabError("missing, unknown or invalid object fields")
    return value


def integer(value: object, maximum: int, minimum: int = 0) -> int:
    if type(value) is not int or not minimum <= value <= maximum:
        raise LabError("integer outside allowed bounds")
    return value


def name(value: object) -> str:
    if not isinstance(value, str) or not value.isascii() or len(value) > 254 or not value.endswith("."):
        raise LabError("name must be absolute ASCII with DNS length limits")
    result = value.lower()
    labels = result[:-1].split(".")
    if labels[-1] != "example" or any(
        not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", label)
        for label in labels
    ):
        raise LabError("invalid label or name outside example.")
    return result


def _pairs(pairs: list[tuple]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise LabError("duplicate JSON key")
        result[key] = value
    return result


def _number(token: str) -> int:
    if len(token) > 12:
        raise LabError("numeric token too long")
    return int(token)


def _unsupported_number(token: str) -> None:
    raise LabError("only integer JSON numbers are supported")


def load(data: bytes) -> dict:
    """Bound bytes and lexical nesting before decoding objects; reject ambiguity."""
    if len(data) > MAX_BYTES:
        raise LabError("input exceeds 1 MiB")
    try:
        text = data.decode("utf-8")
    except UnicodeError as exc:
        raise LabError("input must be UTF-8") from exc
    depth, quoted, escaped = 0, False, False
    for char in text:
        if quoted:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                quoted = False
        elif char == '"':
            quoted = True
        elif char in "[{":
            depth += 1
            if depth > 8:
                raise LabError("JSON nesting exceeds 8")
        elif char in "]}":
            depth -= 1
    try:
        result = json.loads(text, object_pairs_hook=_pairs, parse_int=_number,
                            parse_float=_unsupported_number, parse_constant=_unsupported_number)
    except (json.JSONDecodeError, RecursionError) as exc:
        raise LabError("invalid JSON") from exc
    _strings(result)
    return result


def _strings(value: object) -> None:
    if isinstance(value, str):
        if len(value) > 254 or any(ord(c) < 32 or ord(c) == 127 or 0xD800 <= ord(c) <= 0xDFFF for c in value):
            raise LabError("string exceeds bounds or contains controls/surrogates")
    elif isinstance(value, dict):
        for key, child in value.items():
            _strings(key)
            _strings(child)
    elif isinstance(value, list):
        for child in value:
            _strings(child)


def validate(document: dict) -> list[dict]:
    """Normalize all events before replay, rejecting unsupported input atomically."""
    root = fields(document, {"version", "events"})
    integer(root["version"], 1, 1)
    if not isinstance(root["events"], list) or len(root["events"]) > MAX_EVENTS:
        raise LabError("events must be an array of at most 256")
    events, previous = [], 0
    extra = {"query": (set(), set()), "store_rrset": ({"ttl_s", "records"}, set()),
             "store_negative": ({"kind"}, {"soa"}), "store_failure": (set(), {"duration_s"})}
    for raw in root["events"]:
        if not isinstance(raw, dict) or not isinstance(raw.get("op"), str) or raw["op"] not in extra:
            raise LabError("unknown event operation")
        required, optional = extra[raw["op"]]
        event = dict(fields(raw, {"op", "at_ms", "name", "type"} | required, optional))
        at = integer(event["at_ms"], 86400000)
        if at < previous:
            raise LabError("event time decreased")
        previous = at
        event["name"] = name(event["name"])
        if not isinstance(event["type"], str) or event["type"] not in TYPES:
            raise LabError("unsupported record type")
        kind = event["op"]
        if kind == "store_rrset":
            event["ttl_s"] = integer(event["ttl_s"], 86400)
            records = event["records"]
            if not isinstance(records, list) or not 1 <= len(records) <= 32:
                raise LabError("RRset must contain 1..32 records")
            if event["type"] == "CNAME":
                if len(records) != 1:
                    raise LabError("CNAME must have one target")
                records = [name(records[0])]
            else:
                records = [_address(record, event["type"]) for record in records]
            if len(set(records)) != len(records):
                raise LabError("duplicate canonical record")
            event["records"] = records
        elif kind == "store_negative":
            if event["type"] == "CNAME" or event["kind"] not in ("NXDOMAIN", "NODATA"):
                raise LabError("unsupported negative category/type")
            if "soa" in event:
                soa = dict(fields(event["soa"], {"owner", "ttl_s", "minimum_s"}))
                soa["owner"] = name(soa["owner"])
                owner = soa["owner"]
                if event["name"] != owner and not event["name"].endswith("." + owner):
                    raise LabError("SOA owner is not an ancestor")
                integer(soa["ttl_s"], 86400)
                integer(soa["minimum_s"], 86400)
                event["soa"] = soa
        elif kind == "store_failure":
            if event["type"] == "CNAME":
                raise LabError("failure type must be A or AAAA")
            event["duration_s"] = integer(event.get("duration_s", 5), 300, 1)
        events.append(event)
    return events


def _address(record: object, record_type: str) -> str:
    if not isinstance(record, str):
        raise LabError("address record must be a string")
    try:
        address = ipaddress.ip_address(record)
    except ValueError as exc:
        raise LabError("invalid address") from exc
    if (record_type == "A" and address.version == 4 and any(address in n for n in DOC_V4)) or (
        record_type == "AAAA" and address.version == 6 and "%" not in record and address in DOC_V6
    ):
        return str(address)
    raise LabError("address outside the type's documentation ranges")


@dataclass(frozen=True)
class Entry:
    """Independent cache object; TTL never changes another object's lifetime."""
    category: str
    owner: str
    record_type: str
    inserted: int
    expires: int
    records: tuple[str, ...] = ()

    def evidence(self, now: int) -> dict:
        return {"category": self.category, "key": [self.owner, self.record_type, "IN"],
                "inserted_ms": self.inserted, "expires_ms": self.expires,
                "remaining_ms": self.expires - now, "records": list(self.records)}


class Cache:
    """One bounded store with disjoint categories and frozen transition policy."""
    def __init__(self) -> None:
        self.entries: dict[tuple[str, str, str], Entry] = {}

    def evict(self, now: int) -> None:
        self.entries = {key: value for key, value in self.entries.items() if value.expires > now}

    def get(self, category: str, owner: str, record_type: str) -> Entry | None:
        return self.entries.get((category, owner, record_type))

    def query(self, owner: str, record_type: str, now: int) -> dict:
        hops, seen = [], set()
        terminal = owner
        if record_type != "CNAME":
            while (alias := self.get("positive", terminal, "CNAME")) is not None:
                if terminal in seen:
                    return self._result("alias_cycle", terminal, hops)
                if len(hops) >= 8:
                    return self._result("alias_depth", terminal, hops)
                seen.add(terminal)
                hops.append(alias.evidence(now))
                terminal = alias.records[0]
        positive = self.get("positive", terminal, record_type)
        if positive:
            return self._result("positive", terminal, hops, positive.evidence(now))
        if record_type != "CNAME":
            for category, key_type, decision in (("NXDOMAIN", "*", "NXDOMAIN"),
                    ("NODATA", record_type, "NODATA"), ("failure", record_type, "suppressed_failure")):
                entry = self.get(category, terminal, key_type)
                if entry:
                    return self._result(decision, terminal, hops, entry.evidence(now))
        return self._result("needs_information", terminal, hops)

    @staticmethod
    def _result(decision: str, terminal: str, hops: list, evidence: dict | None = None) -> dict:
        explanations = {"positive": "Reusable cached data; no connection is inferred.",
                        "NXDOMAIN": "Cached exact terminal-name denial; alias and descendants are not denied.",
                        "NODATA": "Cached denial of this terminal type only.",
                        "suppressed_failure": "Completed failure cached; existence remains unknown.",
                        "needs_information": "No reusable terminal data; existence remains unknown.",
                        "alias_cycle": "Cached alias cycle; no denial is inferred.",
                        "alias_depth": "Model alias depth limit; no denial is inferred."}
        result = {"decision": decision, "terminal": terminal, "hops": hops,
                  "explanation": explanations[decision]}
        if evidence is not None:
            result["evidence"] = evidence
        return result

    def store(self, event: dict) -> dict:
        owner, rtype, now = event["name"], event["type"], event["at_ms"]
        operation = event["op"]
        if operation == "store_negative" and "soa" not in event:
            return {"decision": "uncached", "explanation": "Missing SOA; reusable state unchanged."}
        ttl = (min(event["soa"]["ttl_s"], event["soa"]["minimum_s"])
               if operation == "store_negative" else event.get("ttl_s", event.get("duration_s", 5)))
        if ttl == 0:
            return {"decision": "uncached", "explanation": "TTL zero; reusable state unchanged."}
        alias = self.get("positive", owner, "CNAME")
        if operation in ("store_negative", "store_failure") and alias:
            raise LabError("negative/failure insertion must identify terminal, not cached alias")
        if operation == "store_failure":
            if self.query(owner, rtype, now)["decision"] in ("positive", "NXDOMAIN", "NODATA"):
                raise LabError("failure contradicts reusable useful data")
            category, key_type = "failure", rtype
            remove = lambda entry: entry.category == "failure" and entry.record_type == rtype
        elif operation == "store_rrset":
            category, key_type = "positive", rtype
            if rtype == "CNAME":
                remove = lambda entry: True
            else:
                remove = lambda entry: entry.record_type in (rtype, "CNAME", "*")
        elif event["kind"] == "NXDOMAIN":
            category, key_type = "NXDOMAIN", "*"
            remove = lambda entry: True
        else:
            category, key_type = "NODATA", rtype
            remove = lambda entry: entry.record_type in (rtype, "*")
        # Removal is owner-local; useful A refresh must preserve AAAA denials/failures.
        removed = [key for key, entry in self.entries.items() if entry.owner == owner and remove(entry)]
        if len(self.entries) - len(removed) + 1 > MAX_ENTRIES:
            raise LabError("combined cache exceeds 256 entries")
        for key in removed:
            del self.entries[key]
        entry = Entry(category, owner, key_type, now, now + ttl * 1000, tuple(event.get("records", ())))
        self.entries[(category, owner, key_type)] = entry
        return {"decision": "stored", "evidence": entry.evidence(now),
                "removed_keys": [list(key) for key in sorted(removed)],
                "explanation": "Inserted under the documented model transition policy."}


def replay(document: dict) -> dict:
    """Validate and replay entirely in memory without clock or network access."""
    events = validate(document)
    cache, timeline = Cache(), []
    for index, event in enumerate(events):
        cache.evict(event["at_ms"])
        outcome = (cache.query(event["name"], event["type"], event["at_ms"])
                   if event["op"] == "query" else cache.store(event))
        timeline.append({"index": index, "at_ms": event["at_ms"], "op": event["op"],
                         "name": event["name"], "type": event["type"], **outcome})
    return {"version": 1, "model": "offline-normalized-cache-subset", "timeline": timeline}


def render(result: dict, output_format: str = "json") -> bytes:
    """Serialize before writing, enforcing the final output budget."""
    if output_format == "json":
        text = json.dumps(result, indent=2, ensure_ascii=True) + "\n"
    elif output_format == "text":
        text = "Offline DNS cache teaching model (IN); no live resolution.\n"
        for row in result["timeline"]:
            text += f'{row["at_ms"]}ms {row["op"]} {row["name"]} {row["type"]}: {row["decision"]}\n'
            for hop in row.get("hops", []):
                text += f'  alias {hop["key"][0]} -> {hop["records"][0]} remaining={hop["remaining_ms"]}ms\n'
            if "terminal" in row:
                text += f'  terminal={row["terminal"]}\n'
            if "evidence" in row:
                evidence = row["evidence"]
                text += f'  key={evidence["key"]} expires={evidence["expires_ms"]}ms remaining={evidence["remaining_ms"]}ms\n'
            text += f'  {row["explanation"]}\n'
    else:
        raise LabError("unknown output format")
    encoded = text.encode("utf-8")
    if len(encoded) > MAX_BYTES:
        raise LabError("output exceeds 1 MiB")
    return encoded


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scenario", help="UTF-8 normalized JSON scenario")
    parser.add_argument("--format", choices=("json", "text"), default="json")
    args = parser.parse_args(argv)
    try:
        with open(args.scenario, "rb") as stream:
            document = load(stream.read(MAX_BYTES + 1))
        output = render(replay(document), args.format)
        sys.stdout.buffer.write(output)
        return 0
    except (LabError, OSError) as exc:
        # Do not echo input/path contents, which may contain terminal controls or private data.
        message = str(exc) if isinstance(exc, LabError) else "input/output operation failed"
        print("cache-lab: " + message, file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
