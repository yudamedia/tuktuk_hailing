from . import __version__ as app_version

app_name = "tuktuk_hailing"
app_title = "Tuktuk Hailing"
app_publisher = "Sunny Tuktuk"
app_description = "Ride hailing system for Sunny Tuktuk"
app_email = "info@sunnytuktuk.com"
app_license = "MIT"

# Includes in <head>
app_include_css = "/assets/tuktuk_hailing/css/tuktuk_hailing.css"
app_include_js = "/assets/tuktuk_hailing/js/tuktuk_hailing.js"

# include js, css files in header of web template
web_include_css = "/assets/tuktuk_hailing/css/tuktuk_hailing.css"
web_include_js = "/assets/tuktuk_hailing/js/tuktuk_hailing.js"

# include js in doctype views
doctype_js = {
    "TukTuk Driver": "public/js/tuktuk_driver_hailing.js",
}

# Scheduled Tasks
scheduler_events = {
    "cron": {
        "*/5 * * * *": [
            "tuktuk_hailing.api.location.cleanup_stale_locations"
        ]
    }
}

fixtures = [
    {"dt": "Workspace", "filters": [["name", "=", "Tuktuk Hailing"]]}
]
