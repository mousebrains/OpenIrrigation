#
# Email alerts and reports to their subscribers
#
import sys
import os.path
import getpass
import logging
import argparse
import DB
import traceback
import socket
import smtplib
from email.mime.text import MIMEText

# Where an alert goes when nobody subscribes to its report type.  Postfix
# delivers 'root' through /etc/aliases, so an alarm is never silently dropped
# just because the subscription list is empty.
FALLBACK = ['root']

def recipients(cur, key:str) -> list[str]:
    """ Email addresses subscribed to the webList 'reports' entry `key` """
    cur.execute('SELECT email.email AS addr FROM emailReports'
                ' INNER JOIN email ON email.id=emailReports.email'
                ' INNER JOIN webList ON webList.id=emailReports.report'
                " WHERE webList.grp='reports' AND webList.key=%s;", (key,))
    return [r['addr'] if isinstance(r, dict) else r[0] for r in cur.fetchall()]

def sendReport(cur, key:str, subject:str, body:str, logger:logging.Logger,
        mailFrom:str | None = None, fallback:bool = True) -> list[str]:
    """ Email `body` to the `key` report subscribers

    With no subscribers the message goes to FALLBACK instead (unless
    fallback=False, e.g. for routine reports), and the log says so.  Returns
    the addresses used; [] when nothing was sent.  SMTP errors propagate, so a
    caller can leave its "already notified" state alone and retry later.
    """
    addrs = recipients(cur, key)
    if not addrs:
        if not fallback:
            logger.warning("No '%s' email subscribers, nothing sent: %s", key, subject)
            return []
        logger.warning("No '%s' email subscribers, sending to %s: %s",
                       key, ','.join(FALLBACK), subject)
        addrs = FALLBACK
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = mailFrom or (getpass.getuser() + '@' + socket.getfqdn())
    msg['To'] = ', '.join(addrs)
    # timeout so a wedged local MTA can't hang the caller
    with smtplib.SMTP('localhost', timeout=30) as s:
        s.send_message(msg)
    return addrs

def formatException(exc:BaseException | None = None) -> str:
    """ Render exc, or the exception currently being handled, as a traceback

    traceback.format_exc() only works while an except block is on the stack; a
    caller which reports the failure after the handler has exited gets the
    useless string 'NoneType: None'.  Pass the exception object in to avoid that.
    """
    if exc is not None:
        return ''.join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    if sys.exc_info()[0] is not None: # Called from inside an except block
        return traceback.format_exc()
    return 'No exception information available\n'

def onException(args:argparse.Namespace, logger:logging.Logger,
        exc:BaseException | None = None) -> None:
    try:
        # The recipient list lives in the database, so a failure which is itself
        # a database outage cannot be mailed; it is left to the log and systemd.
        fqdn = socket.getfqdn()
        item = os.path.basename(sys.argv[0])
        cnt = "command line:\n" + ' '.join(sys.argv) + "\n\n"
        cnt+= formatException(exc)
        with DB.DB(args.db, logger) as db, db.cursor() as cur:
            sendReport(cur, 'systemd', '{} failed on {}'.format(item, fqdn), cnt, logger,
                       mailFrom=getattr(args, 'mailFrom', None))
    except Exception:
        logger.exception('Exception processing during Notify')
