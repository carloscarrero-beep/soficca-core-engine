from soficca_core.engine import generate_report
from soficca_core.chat_state import new_state


def run_demo():
    user = {"name": "Carlos", "dob": "1993-01-01"}

    # Start with an empty chat_state
    chat_state = new_state(user_profile=user)

    # A scripted conversation (user messages)
    user_messages = [
        "",  # first call: no user text yet, assistant should greet + ask reason
        "I want help with my sexual performance. Sometimes it works, sometimes it doesn't.",
        "It doesn't last long enough sometimes.",
        "Not always. I have good days and bad days.",
        "Desire is still there, but my body doesn't always respond.",
        "Stress is pretty high lately.",
        "Morning erections are reduced compared to before.",
        "I'd like medication support.",
    ]

    for i, text in enumerate(user_messages):
        input_data = {
            "user": user,
            "measurements": [],
            "context": {
                "chat_text": text,
                "chat_state": chat_state,
            },
        }

        result = generate_report(input_data)
        report = result["report"]
        chat = report["chat"]

        assistant = chat.get("assistant_message")
        phase = chat.get("phase")
        done = chat.get("done")

        path = report.get("scores", {}).get("path", "PATH_MORE_QUESTIONS")
        reasons = report.get("reasons", [])
        recs = report.get("recommendations", [])
        flags = report.get("flags", [])

        print("\n" + "=" * 70)
        print(f"TURN {i}")
        print(f"USER: {text!r}")
        print(f"PHASE: {phase} | DONE: {done}")
        print("-" * 70)
        print("PEN:")
        print(assistant)
        print("-" * 70)
        print("DECISION:")
        print("path:", path)
        print("flags:", flags)
        print("reasons:", reasons)
        print("recommendations:", recs)

        # update state for next turn
        chat_state = chat.get("state", chat_state)

    print("\nDemo finished.")


if __name__ == "__main__":
    run_demo()
