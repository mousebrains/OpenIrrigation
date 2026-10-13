#!/usr/bin/env python3
#
# Email the 'systemd' subscribers (root if there are none) that a systemd
# unit failed, with its `systemctl status`. Run by OIFailure@.service, which
# each OpenIrrigation unit names in OnFailure=OIFailure@%n.service.
#
# A unit that keeps failing -- the 2-minute flow watchdog, or a daemon in a
# restart loop -- is reported at most once per --holdoff hours; a stamp file
# per unit in the working directory remembers the last email. If the database
# (which holds the subscriber list) is down, the email goes straight to root.
#
# Oct-2026, Pat Welch, pat@mousebrains.com

import argparse
import datetime
import os
import re
import socket
import subprocess
import sys
import time

import DB
import MyLogger
import Notify


class NoSubscribers:
    """Stands in for a cursor when the database is unreachable, so
    Notify.sendReport() falls back to root."""
    def execute(self, *args):
        pass

    def fetchall(self):
        return []


def stampFile(unit:str) -> str:
    return "OIFailure-" + re.sub(r"[^A-Za-z0-9@._-]", "_", unit) + ".stamp"


def recentlySent(path:str, holdoff:datetime.timedelta) -> bool:
    try:
        return time.time() - os.path.getmtime(path) < holdoff.total_seconds()
    except OSError:
        return False


def unitStatus(unit) -> str:
    # status exits 3 for a failed unit; the text is what matters
    r = subprocess.run(["/bin/systemctl", "status", "--no-pager", "--full",
                        "--lines=40", unit],
                       capture_output=True, text=True, timeout=30, check=False)
    return r.stdout + r.stderr


def report(args, logger) -> None:
    stamp = stampFile(args.unit)
    if recentlySent(stamp, datetime.timedelta(hours=args.holdoff)):
        logger.info("%s failed again; already reported within %g h", args.unit, args.holdoff)
        return
    try:
        status = unitStatus(args.unit)
    except Exception as e:
        status = f"systemctl status {args.unit} failed: {e}\n"
    subject = f"{args.unit} failed on {socket.getfqdn()}"
    body = (f"The systemd unit {args.unit} failed. Further failures of it are"
            f" not reported for {args.holdoff:g} hours.\n\n{status}")
    try:
        with DB.DB(args.db, logger) as db, db.cursor() as cur:
            Notify.sendReport(cur, "systemd", subject, body, logger, mailFrom=args.mailFrom)
    except DB.NoConnection:
        logger.warning("Database unreachable; reporting %s to root", args.unit)
        Notify.sendReport(NoSubscribers(), "systemd", subject, body, logger,
                          mailFrom=args.mailFrom)
    with open(stamp, "w") as fp:
        fp.write(datetime.datetime.now().astimezone().isoformat() + "\n")
    logger.info("Reported the failure of %s", args.unit)


def main():
    parser = argparse.ArgumentParser(description="Email that a systemd unit failed")
    parser.add_argument("--db", required=True, type=str, help="Database name")
    parser.add_argument("--unit", required=True, type=str, help="The unit that failed")
    parser.add_argument("--holdoff", type=float, default=6,
                        help="Hours before the same unit is reported again")
    parser.add_argument("--mailFrom", type=str, help="email source")
    MyLogger.addArgs(parser)
    args = parser.parse_args()

    logger = MyLogger.mkLogger(args, __name__, fmt="%(asctime)s: %(levelname)s: %(message)s")
    try:
        report(args, logger)
    except Exception:
        logger.exception("Unable to report the failure of %s", args.unit)
        sys.exit(1)


if __name__ == "__main__":
    main()
