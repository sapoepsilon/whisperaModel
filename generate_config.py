#!/usr/bin/env python3
"""
Auto-generate command config by scanning the Mac for installed apps and folders.
This creates the mapping that the Swift app uses to execute commands.
"""

import os
import json
import subprocess
from pathlib import Path


def get_installed_apps():
    """Scan for installed applications and create name mappings."""
    apps = {}
    app_dirs = [
        "/Applications",
        os.path.expanduser("~/Applications"),
        "/System/Applications",
        "/System/Applications/Utilities",
    ]

    for app_dir in app_dirs:
        if not os.path.exists(app_dir):
            continue

        for item in os.listdir(app_dir):
            if item.endswith(".app"):
                app_name = item[:-4]  # Remove .app

                # Create lowercase key variations
                key = app_name.lower().replace(" ", "")
                key_with_spaces = app_name.lower()

                apps[key] = app_name
                if key != key_with_spaces:
                    apps[key_with_spaces] = app_name

                # Common aliases
                aliases = get_app_aliases(app_name)
                for alias in aliases:
                    apps[alias] = app_name

    return apps


def get_app_aliases(app_name: str) -> list:
    """Get common aliases for app names."""
    aliases = []
    name_lower = app_name.lower()

    alias_map = {
        "Visual Studio Code": ["vscode", "vs code", "code"],
        "Google Chrome": ["chrome"],
        "Firefox": ["firefox", "ff"],
        "Safari": ["safari"],
        "Terminal": ["terminal", "term"],
        "iTerm": ["iterm", "iterm2"],
        "Sublime Text": ["sublime", "subl"],
        "Adobe Photoshop": ["photoshop", "ps"],
        "Adobe Illustrator": ["illustrator", "ai"],
        "Adobe Premiere Pro": ["premiere"],
        "Final Cut Pro": ["finalcut", "fcp"],
        "Logic Pro": ["logic"],
        "Xcode": ["xcode"],
        "Android Studio": ["android studio", "androidstudio"],
        "IntelliJ IDEA": ["intellij", "idea"],
        "PyCharm": ["pycharm"],
        "WebStorm": ["webstorm"],
        "Slack": ["slack"],
        "Discord": ["discord"],
        "Zoom": ["zoom"],
        "Microsoft Teams": ["teams"],
        "Microsoft Word": ["word"],
        "Microsoft Excel": ["excel"],
        "Microsoft PowerPoint": ["powerpoint", "ppt"],
        "Microsoft Outlook": ["outlook"],
        "Notion": ["notion"],
        "Obsidian": ["obsidian"],
        "Bear": ["bear"],
        "Things": ["things"],
        "Todoist": ["todoist"],
        "Spotify": ["spotify"],
        "Music": ["music", "apple music"],
        "Podcasts": ["podcasts"],
        "TV": ["tv", "apple tv"],
        "Photos": ["photos"],
        "Preview": ["preview"],
        "Finder": ["finder"],
        "System Preferences": ["settings", "preferences", "system settings"],
        "System Settings": ["settings", "preferences", "system preferences"],
        "Activity Monitor": ["activity monitor", "activity", "task manager"],
        "Calculator": ["calculator", "calc"],
        "Calendar": ["calendar", "cal"],
        "Contacts": ["contacts"],
        "Mail": ["mail", "email"],
        "Messages": ["messages", "imessage"],
        "FaceTime": ["facetime"],
        "Notes": ["notes"],
        "Reminders": ["reminders"],
        "TextEdit": ["textedit"],
        "QuickTime Player": ["quicktime"],
        "VLC": ["vlc"],
        "Figma": ["figma"],
        "Sketch": ["sketch"],
        "Arc": ["arc"],
        "Brave Browser": ["brave"],
        "Opera": ["opera"],
        "WhatsApp": ["whatsapp"],
        "Telegram": ["telegram"],
        "Signal": ["signal"],
        "1Password": ["1password", "onepassword"],
        "Bitwarden": ["bitwarden"],
        "Docker": ["docker"],
        "TablePlus": ["tableplus"],
        "Postman": ["postman"],
        "Insomnia": ["insomnia"],
    }

    for app, app_aliases in alias_map.items():
        if app.lower() in name_lower or name_lower in app.lower():
            aliases.extend(app_aliases)

    return aliases


def get_common_folders():
    """Get common folder mappings."""
    home = os.path.expanduser("~")

    folders = {
        "downloads": "~/Downloads",
        "documents": "~/Documents",
        "desktop": "~/Desktop",
        "home": "~",
        "applications": "/Applications",
        "pictures": "~/Pictures",
        "photos": "~/Pictures",
        "movies": "~/Movies",
        "videos": "~/Movies",
        "music": "~/Music",
        "developer": "~/Developer",
        "dev": "~/Developer",
        "projects": "~/Developer",
        "library": "~/Library",
        "trash": "~/.Trash",
    }

    # Add any existing folders in home directory
    for item in os.listdir(home):
        path = os.path.join(home, item)
        if os.path.isdir(path) and not item.startswith("."):
            key = item.lower()
            if key not in folders:
                folders[key] = f"~/{item}"

    return folders


def get_common_urls():
    """Get common website URL mappings."""
    return {
        "google": "https://google.com",
        "github": "https://github.com",
        "youtube": "https://youtube.com",
        "twitter": "https://twitter.com",
        "x": "https://x.com",
        "reddit": "https://reddit.com",
        "linkedin": "https://linkedin.com",
        "facebook": "https://facebook.com",
        "instagram": "https://instagram.com",
        "amazon": "https://amazon.com",
        "netflix": "https://netflix.com",
        "spotify": "https://open.spotify.com",
        "hacker news": "https://news.ycombinator.com",
        "hackernews": "https://news.ycombinator.com",
        "hn": "https://news.ycombinator.com",
        "stack overflow": "https://stackoverflow.com",
        "stackoverflow": "https://stackoverflow.com",
        "so": "https://stackoverflow.com",
        "gmail": "https://mail.google.com",
        "drive": "https://drive.google.com",
        "docs": "https://docs.google.com",
        "sheets": "https://sheets.google.com",
        "notion": "https://notion.so",
        "figma": "https://figma.com",
        "vercel": "https://vercel.com",
        "netlify": "https://netlify.com",
        "aws": "https://console.aws.amazon.com",
        "azure": "https://portal.azure.com",
        "gcp": "https://console.cloud.google.com",
        "heroku": "https://dashboard.heroku.com",
        "digitalocean": "https://cloud.digitalocean.com",
        "cloudflare": "https://dash.cloudflare.com",
        "npm": "https://npmjs.com",
        "pypi": "https://pypi.org",
        "crates": "https://crates.io",
        "docker hub": "https://hub.docker.com",
    }


def get_commands():
    """Get the command templates for each action type."""
    return {
        "open_app": 'open -a "{target}"',
        "quit_app": "osascript -e 'quit app \"{target}\"'",
        "web_search": 'open "https://www.google.com/search?q={query}"',
        "open_url": 'open "{url}"',
        "open_folder": 'open "{path}"',
        "volume": {
            "up": "osascript -e 'set volume output volume ((output volume of (get volume settings)) + 10)'",
            "down": "osascript -e 'set volume output volume ((output volume of (get volume settings)) - 10)'",
            "mute": "osascript -e 'set volume with output muted'",
            "unmute": "osascript -e 'set volume without output muted'",
        },
        "screenshot": "screencapture -i ~/Desktop/screenshot-$(date +%Y%m%d-%H%M%S).png",
        "screenshot_window": "screencapture -w ~/Desktop/screenshot-$(date +%Y%m%d-%H%M%S).png",
        "screenshot_full": "screencapture ~/Desktop/screenshot-$(date +%Y%m%d-%H%M%S).png",
        "window": {
            "close": "osascript -e 'tell application \"System Events\" to keystroke \"w\" using command down'",
            "minimize": "osascript -e 'tell application \"System Events\" to keystroke \"m\" using command down'",
            "fullscreen": "osascript -e 'tell application \"System Events\" to keystroke \"f\" using {command down, control down}'",
            "new_tab": "osascript -e 'tell application \"System Events\" to keystroke \"t\" using command down'",
            "new_window": "osascript -e 'tell application \"System Events\" to keystroke \"n\" using command down'",
        },
        "system": {
            "sleep": "pmset sleepnow",
            "lock": "pmset displaysleepnow",
            "show_desktop": "osascript -e 'tell application \"System Events\" to key code 103'",
            "empty_trash": "osascript -e 'tell application \"Finder\" to empty trash'",
            "spotlight": "osascript -e 'tell application \"System Events\" to keystroke space using command down'",
        },
        "media": {
            "play": "osascript -e 'tell application \"Music\" to play'",
            "pause": "osascript -e 'tell application \"Music\" to pause'",
            "next": "osascript -e 'tell application \"Music\" to next track'",
            "previous": "osascript -e 'tell application \"Music\" to previous track'",
        },
        "keyboard": {
            "copy": "osascript -e 'tell application \"System Events\" to keystroke \"c\" using command down'",
            "paste": "osascript -e 'tell application \"System Events\" to keystroke \"v\" using command down'",
            "cut": "osascript -e 'tell application \"System Events\" to keystroke \"x\" using command down'",
            "undo": "osascript -e 'tell application \"System Events\" to keystroke \"z\" using command down'",
            "redo": "osascript -e 'tell application \"System Events\" to keystroke \"z\" using {command down, shift down}'",
            "save": "osascript -e 'tell application \"System Events\" to keystroke \"s\" using command down'",
            "find": "osascript -e 'tell application \"System Events\" to keystroke \"f\" using command down'",
            "select_all": "osascript -e 'tell application \"System Events\" to keystroke \"a\" using command down'",
        },
        "info": {
            "time": "date +%H:%M:%S",
            "date": "date",
            "battery": "pmset -g batt",
        },
        "dark_mode": "osascript -e 'tell app \"System Events\" to tell appearance preferences to set dark mode to not dark mode'",
    }


def generate_config():
    """Generate the complete configuration."""
    print("Scanning for installed applications...")
    apps = get_installed_apps()
    print(f"Found {len(apps)} app mappings")

    print("Generating folder mappings...")
    folders = get_common_folders()
    print(f"Found {len(folders)} folder mappings")

    print("Adding URL mappings...")
    urls = get_common_urls()
    print(f"Added {len(urls)} URL mappings")

    config = {
        "apps": apps,
        "folders": folders,
        "urls": urls,
        "commands": get_commands(),
    }

    return config


def main():
    config = generate_config()

    # Save config
    config_path = "whispera_config.json"
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)

    print(f"\nConfig saved to {config_path}")
    print(f"Total app mappings: {len(config['apps'])}")
    print(f"Total folder mappings: {len(config['folders'])}")
    print(f"Total URL mappings: {len(config['urls'])}")

    # Show some examples
    print("\nExample app mappings:")
    for key, value in list(config["apps"].items())[:10]:
        print(f"  '{key}' -> '{value}'")

    print("\nYour Swift app can now:")
    print("  1. Get model output: {\"action\":\"open_app\",\"target\":\"vscode\"}")
    print("  2. Look up 'vscode' in config['apps'] -> 'Visual Studio Code'")
    print("  3. Execute: open -a \"Visual Studio Code\"")


if __name__ == "__main__":
    main()
