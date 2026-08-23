from main import app as flask_app
app = flask_app

@flask_app.route("/api", methods=["GET", "POST"])
def api_entry():
    from flask import request
    if request.method == "GET":
        return "Bot Running", 200
    # POST wale ko main wale webhook pe bhej do
    if "/" in flask_app.url_map.iter_rules().__str__():
        pass
    # Call the original webhook function
    for rule in flask_app.url_map.iter_rules():
        if "webhook" in str(rule.endpoint) or rule.rule == "/":
            try:
                return flask_app.view_functions[rule.endpoint]()
            except:
                pass
    return "OK", 200
