from flask import Flask, request, jsonify
import json

app = Flask(__name__)

# In-memory store keyed by session_id
store = {}


@app.route("/append", methods=["POST"])
def append_rows():
    data = request.get_json()

    session_id = data.get("session_id")
    scripts_rows = data.get("scripts_rows", "[]")
    summary_rows = data.get("summary_rows", "[]")
    group_type = data.get("group_type", "l3")

    # Metadata — passed on first L3 call only
    base_tc_id = data.get("base_tc_id")
    total_l3_groups = data.get("total_l3_groups")
    total_modifier_groups = data.get("total_modifier_groups")

    # Lightweight group structure — UST IDs only
    l3_group_ust_ids = data.get("l3_group_ust_ids")
    modifier_group_ust_ids = data.get("modifier_group_ust_ids")

    if not session_id:
        return jsonify({"error": "session_id is required"}), 400

    # Parse incoming rows
    try:
        scripts = json.loads(scripts_rows) if isinstance(scripts_rows, str) else scripts_rows
        summary = json.loads(summary_rows) if isinstance(summary_rows, str) else summary_rows
    except Exception as e:
        return jsonify({"error": f"Invalid JSON in rows: {str(e)}"}), 400

    # Initialise session if first call
    if session_id not in store:
        store[session_id] = {
            "scripts": [],
            "summary": [],
            "groups_appended": 0,
            "modifier_groups_appended": 0,
            "base_tc_id": None,
            "total_l3_groups": 0,
            "total_modifier_groups": 0,
            "l3_group_ust_ids": [],
            "modifier_group_ust_ids": []
        }

    session = store[session_id]

    # Store metadata on first call if provided
    if base_tc_id and not session["base_tc_id"]:
        session["base_tc_id"] = base_tc_id

    if total_l3_groups and session["total_l3_groups"] == 0:
        session["total_l3_groups"] = int(total_l3_groups)

    if total_modifier_groups and session["total_modifier_groups"] == 0:
        session["total_modifier_groups"] = int(total_modifier_groups)

    if l3_group_ust_ids and not session["l3_group_ust_ids"]:
        parsed = json.loads(l3_group_ust_ids) if isinstance(l3_group_ust_ids, str) else l3_group_ust_ids
        session["l3_group_ust_ids"] = parsed

    if modifier_group_ust_ids and not session["modifier_group_ust_ids"]:
        parsed = json.loads(modifier_group_ust_ids) if isinstance(modifier_group_ust_ids, str) else modifier_group_ust_ids
        session["modifier_group_ust_ids"] = parsed

    # Append rows
    session["scripts"].extend(scripts)
    session["summary"].extend(summary)

    # Increment the right counter
    if group_type == "modifier":
        session["modifier_groups_appended"] += 1
    else:
        session["groups_appended"] += 1

    return jsonify({
        "status": "appended",
        "session_id": session_id,
        "group_type": group_type,
        "groups_appended": session["groups_appended"],
        "modifier_groups_appended": session["modifier_groups_appended"],
        "total_scripts_rows": len(session["scripts"]),
        "total_summary_rows": len(session["summary"])
    })


@app.route("/retrieve", methods=["GET"])
def retrieve_rows():
    session_id = request.args.get("session_id")

    if not session_id:
        return jsonify({"error": "session_id is required"}), 400

    if session_id not in store:
        return jsonify({
            "session_id": session_id,
            "scripts_rows": "[]",
            "summary_rows": "[]",
            "total_scripts_rows": 0,
            "total_summary_rows": 0,
            "groups_appended": 0,
            "modifier_groups_appended": 0
        })

    session = store[session_id]
    return jsonify({
        "session_id": session_id,
        "scripts_rows": json.dumps(session["scripts"]),
        "summary_rows": json.dumps(session["summary"]),
        "total_scripts_rows": len(session["scripts"]),
        "total_summary_rows": len(session["summary"]),
        "groups_appended": session["groups_appended"],
        "modifier_groups_appended": session["modifier_groups_appended"]
    })


@app.route("/status", methods=["GET"])
def status():
    session_id = request.args.get("session_id")

    if session_id and session_id in store:
        session = store[session_id]
        return jsonify({
            "session_id": session_id,
            "groups_appended": session["groups_appended"],
            "modifier_groups_appended": session["modifier_groups_appended"],
            "total_l3_groups": session["total_l3_groups"],
            "total_modifier_groups": session["total_modifier_groups"],
            "base_tc_id": session["base_tc_id"],
            "l3_group_ust_ids": session["l3_group_ust_ids"],
            "modifier_group_ust_ids": session["modifier_group_ust_ids"],
            "total_scripts_rows": len(session["scripts"]),
            "total_summary_rows": len(session["summary"])
        })

    if session_id and session_id not in store:
        return jsonify({
            "session_id": session_id,
            "groups_appended": 0,
            "modifier_groups_appended": 0,
            "total_l3_groups": 0,
            "total_modifier_groups": 0,
            "base_tc_id": None,
            "l3_group_ust_ids": [],
            "modifier_group_ust_ids": [],
            "total_scripts_rows": 0,
            "total_summary_rows": 0
        })

    return jsonify({
        "status": "ok",
        "sessions_active": list(store.keys())
    })


@app.route("/clear", methods=["POST"])
def clear_session():
    data = request.get_json()
    session_id = data.get("session_id")

    if not session_id:
        return jsonify({"error": "session_id is required"}), 400

    if session_id in store:
        del store[session_id]

    return jsonify({
        "status": "cleared",
        "session_id": session_id
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
