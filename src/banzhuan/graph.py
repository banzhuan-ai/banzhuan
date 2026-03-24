from __future__ import annotations

import copy
import time
from typing import Any, Dict, List, Optional, Sequence, TypedDict


class BuilderGraphPosition(TypedDict, total=False):
    x: float
    y: float


class BuilderGraphBlock(TypedDict, total=False):
    id: str
    type: str
    position: BuilderGraphPosition
    params: Dict[str, Any]


class BuilderConnection(TypedDict, total=False):
    id: str
    sourceBlockId: str
    sourceHandle: str
    targetBlockId: str
    targetHandle: str


class BuilderGraph(TypedDict, total=False):
    name: str
    description: str
    market: str
    blocks: List[BuilderGraphBlock]
    connections: List[BuilderConnection]


class BuilderCommand(TypedDict, total=False):
    type: str
    blockType: str
    id: str
    position: BuilderGraphPosition
    params: Dict[str, Any]
    sourceBlockId: str
    sourceHandle: str
    targetBlockId: str
    targetHandle: str
    blockId: str
    param: str
    value: Any
    market: str


def empty_builder_graph(market: str = "HYPE-USD") -> BuilderGraph:
    return {
        "name": "Strategy",
        "description": "",
        "market": market,
        "blocks": [],
        "connections": [],
    }


def _clone_graph(current_graph: Optional[BuilderGraph]) -> BuilderGraph:
    if not current_graph:
        return empty_builder_graph()
    return {
        "name": str(current_graph.get("name") or "Strategy"),
        "description": str(current_graph.get("description") or ""),
        "market": str(current_graph.get("market") or "HYPE-USD"),
        "blocks": copy.deepcopy(list(current_graph.get("blocks") or [])),
        "connections": copy.deepcopy(list(current_graph.get("connections") or [])),
    }


def apply_builder_commands(
    current_graph: Optional[BuilderGraph],
    commands: Sequence[BuilderCommand],
) -> BuilderGraph:
    """Apply production Builder command deltas to a local graph snapshot."""

    graph = _clone_graph(current_graph)

    for command in commands:
        cmd_type = str(command.get("type") or "")

        if cmd_type == "clear_canvas":
            graph["blocks"] = []
            graph["connections"] = []
            continue

        if cmd_type == "set_canvas_market" and command.get("market"):
            graph["market"] = str(command["market"])
            continue

        if (
            cmd_type == "add_block"
            and command.get("blockType")
            and command.get("id")
            and command.get("position")
        ):
            block_id = str(command["id"])
            graph["blocks"] = [
                block for block in graph["blocks"] if str(block.get("id") or "") != block_id
            ]
            graph["blocks"].append(
                {
                    "id": block_id,
                    "type": str(command["blockType"]),
                    "position": dict(command.get("position") or {}),
                    "params": dict(command.get("params") or {}),
                }
            )
            continue

        if (
            cmd_type == "connect"
            and command.get("sourceBlockId")
            and command.get("targetBlockId")
        ):
            target_block_id = str(command["targetBlockId"])
            target_handle = str(command.get("targetHandle") or "value")
            source_handle = str(command.get("sourceHandle") or "value")

            graph["connections"] = [
                connection
                for connection in graph["connections"]
                if not (
                    str(connection.get("targetBlockId") or "") == target_block_id
                    and str(connection.get("targetHandle") or "value") == target_handle
                )
            ]

            graph["connections"].append(
                {
                    "id": f"e_{command['sourceBlockId']}_{target_block_id}_{time.time_ns()}",
                    "sourceBlockId": str(command["sourceBlockId"]),
                    "sourceHandle": source_handle,
                    "targetBlockId": target_block_id,
                    "targetHandle": target_handle,
                }
            )
            continue

        if cmd_type == "set_param" and command.get("blockId") and command.get("param") is not None:
            block_id = str(command["blockId"])
            param_name = str(command["param"])
            for block in graph["blocks"]:
                if str(block.get("id") or "") == block_id:
                    params = dict(block.get("params") or {})
                    params[param_name] = command.get("value")
                    block["params"] = params
                    break
            continue

        if cmd_type == "delete_block" and command.get("blockId"):
            block_id = str(command["blockId"])
            graph["blocks"] = [
                block for block in graph["blocks"] if str(block.get("id") or "") != block_id
            ]
            graph["connections"] = [
                connection
                for connection in graph["connections"]
                if str(connection.get("sourceBlockId") or "") != block_id
                and str(connection.get("targetBlockId") or "") != block_id
            ]

    return graph
