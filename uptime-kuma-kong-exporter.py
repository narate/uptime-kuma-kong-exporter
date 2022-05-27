#!/usr/bin/env python3

import argparse
import copy
import json
import requests

parser = argparse.ArgumentParser(description="Uptime Kuma Kong exporter")

parser.add_argument(
    "--kong-admin",
    dest="kong_admin_url",
    type=str,
    default="http://127.0.0.1:8001",
    help="kong admin api url",
)

parser.add_argument(
    "--out",
    dest="output_file",
    type=str,
    default="uptime-kuma-kong-export.json",
    help="output file name [.json]",
)

parser.add_argument(
    "--color",
    dest="tag_color",
    type=str,
    default="#0D4E7F",
    help="tag color in HEX",
)

parser.add_argument(
    "--dns",
    dest="dns_server",
    type=str,
    default="1.1.1.1",
    help="dns resolver server",
)

parser.add_argument(
    "--statuscodes",
    dest="status_codes",
    nargs="+",
    default=["200-299", "300-399", "400-499"],
    help="accepted status codes",
)

parser.add_argument(
    "--https",
    dest="use_https",
    default=False,
    action="store_true",
    help="use https for url",
)

args = parser.parse_args()

monitor_fields = {
    "name": "Monitor name",
    "url": "http://example.com/",
    "method": "GET",
    "hostname": None,
    "port": None,
    "maxretries": 2,
    "weight": 2000,
    "active": 1,
    "type": "http",
    "interval": 60,
    "retryInterval": 60,
    "keyword": None,
    "expiryNotification": True,
    "ignoreTls": False,
    "upsideDown": False,
    "maxredirects": 10,
    "accepted_statuscodes": ["200-299"],
    "dns_resolve_type": "A",
    "dns_resolve_server": args.dns_server,
    "dns_last_result": None,
    "proxyId": None,
    "notificationIDList": {},
    "tags": [],
    "mqttUsername": "",
    "mqttPassword": "",
    "mqttTopic": "",
    "mqttSuccessMessage": "",
    "headers": None,
    "body": None,
    "basic_auth_user": None,
    "basic_auth_pass": None,
    "pushToken": None,
}


def get_routes():
    print("Getting Kong Routes...")
    routes = []
    try:
        res = requests.get(f"{args.kong_admin_url}/routes").json() or {}
        routes += res["data"] or []
        while res.get("next", None):
            next = res["next"]
            print(f"Next: {next}")
            try:
                res = requests.get(f"{args.kong_admin_url}{next}").json() or {}
                routes += res["data"] or []
            except requests.exceptions.RequestException as e:
                raise SystemExit(e)

    except requests.exceptions.RequestException as e:
        raise SystemExit(e)

    return routes


def create_monitor_list():
    routes = get_routes()

    print("Creating Kuma Uptime monitor list...")

    monitor_list = []
    for r in routes:
        hosts = r["hosts"] or ["kong:8000"]
        paths = r["paths"] or ["/"]
        for h in hosts:
            for p in paths:
                m = copy.copy(monitor_fields)
                m["accepted_statuscodes"] = args.status_codes
                m["name"] = r["name"]
                m["url"] = f"http://{h}{p}"
                if args.use_https is True:
                    m["url"] = f"https://{h}{p}"

                m["type"] = "http"
                if r["tags"]:
                    _tags = []
                    for t in r["tags"]:
                        _tags.append({"value": "", "name": t, "color": args.tag_color})
                    m["tags"] = _tags
                else:
                    m["tags"] = [
                        {
                            "value": "Kong API Gateway",
                            "name": "Kong",
                            "color": args.tag_color,
                        }
                    ]

                monitor_list.append(m)
    print(f"Done for {str(len(monitor_list))} urls")
    return monitor_list


print(f"Found Kong admin API: {args.kong_admin_url}")

export_data = {
    "version": "1.15.1",
    "notificationList": [],
    "monitorList": create_monitor_list(),
}

with open(args.output_file, "w") as f:
    f.write(json.dumps(export_data, ensure_ascii=False, indent=2))

print(f"Exported to {args.output_file}")
