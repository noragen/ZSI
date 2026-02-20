"""Streaming parse prototype for large SOAP payload inspection."""

from __future__ import annotations

import io
import xml.etree.ElementTree as ET


def stream_scan_envelope(xml_payload):
    """Return lightweight envelope/body summary using iterparse.

    Prototype goals:
    - lower peak memory than full DOM parse for preflight checks
    - provide body-root metadata for large messages
    """
    if isinstance(xml_payload, bytes):
        stream = io.BytesIO(xml_payload)
    elif isinstance(xml_payload, str):
        stream = io.BytesIO(xml_payload.encode("utf-8"))
    else:
        stream = xml_payload

    depth = 0
    max_depth = 0
    element_count = 0
    in_body = False
    body_root = None

    for event, elem in ET.iterparse(stream, events=("start", "end")):
        if event == "start":
            depth += 1
            element_count += 1
            if depth > max_depth:
                max_depth = depth
            local = elem.tag.split("}", 1)[-1] if "}" in elem.tag else elem.tag
            if local == "Body":
                in_body = True
            elif in_body and body_root is None:
                body_root = elem.tag
        else:
            local = elem.tag.split("}", 1)[-1] if "}" in elem.tag else elem.tag
            if local == "Body":
                in_body = False
            depth -= 1

    return {
        "element_count": element_count,
        "max_depth": max_depth,
        "body_root_tag": body_root,
    }
