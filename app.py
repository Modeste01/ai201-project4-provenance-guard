import uuid
from flask import Flask, request, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from detector import llm_detect, stylometric_detect
from scorer import compute_confidence, generate_label
from audit import log_submission, log_appeal, get_log

app = Flask(__name__)

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=[],
    storage_uri="memory://",
)


@app.route("/")
def index():
    return jsonify({
        "name": "Provenance Guard API",
        "endpoints": {
            "POST /submit": "Submit text for AI detection analysis",
            "POST /appeal": "Appeal a classification decision",
            "GET /log": "View audit log entries",
        }
    })


@app.route("/submit", methods=["POST"])
@limiter.limit("10 per minute;100 per day")
def submit():
    data = request.get_json()
    if not data or not data.get("text"):
        return jsonify({"error": "Missing 'text' field"}), 400

    text = data["text"]
    creator_id = data.get("creator_id", "anonymous")
    content_id = str(uuid.uuid4())
    word_count = len(text.split())

    llm_score = llm_detect(text)
    stylo_score = stylometric_detect(text)
    confidence = compute_confidence(llm_score, stylo_score, word_count)
    label_info = generate_label(confidence)

    entry = {
        "type": "submission",
        "content_id": content_id,
        "creator_id": creator_id,
        "confidence": confidence,
        "llm_score": llm_score,
        "stylometric_score": stylo_score,
        "label": label_info["label"],
        "status": "classified",
    }
    log_submission(entry)

    return jsonify({
        "content_id": content_id,
        "confidence": confidence,
        "label": label_info["label"],
        "label_message": label_info["message"],
        "signals": {
            "llm": llm_score,
            "stylometric": stylo_score,
        },
    })


@app.route("/appeal", methods=["POST"])
@limiter.limit("5 per hour")
def appeal():
    data = request.get_json()
    if not data or not data.get("content_id") or not data.get("creator_reasoning"):
        return jsonify({"error": "Missing 'content_id' or 'creator_reasoning'"}), 400

    content_id = data["content_id"]
    creator_reasoning = data["creator_reasoning"]

    result = log_appeal(content_id, creator_reasoning)
    if result is None:
        return jsonify({"error": "Content ID not found"}), 404

    return jsonify({
        "content_id": content_id,
        "status": "under_review",
        "message": "Your appeal has been received and will be reviewed.",
    })


@app.route("/log", methods=["GET"])
@limiter.limit("30 per minute")
def view_log():
    entries = get_log()
    return jsonify({"entries": entries})


if __name__ == "__main__":
    app.run(debug=True)
