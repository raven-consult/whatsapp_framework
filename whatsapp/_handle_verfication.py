from werkzeug import Request, Response


def handle_verification(request: Request, webhook_initialize_string: str):
    hub_mode = request.args.get("hub.mode", "")
    hub_challenge = request.args.get("hub.challenge", "")
    hub_verify_token = request.args.get("hub.verify_token", "")

    if hub_mode == "subscribe" and hub_verify_token == webhook_initialize_string:
        return Response(hub_challenge, 200)
