#
# Called with an exception and send an email if needed
#
import sys
import os.path
import logging
import argparse
import DB
import traceback
import socket
import smtplib
from email.mime.text import MIMEText

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
        email = []
        sql = 'SELECT email.email FROM email' \
                + ' LEFT JOIN emailReports ON email.id=emailReports.email' \
                + ' LEFT JOIN webList ON webList.id=emailReports.report' \
                + " WHERE webList.key='systemd';"
        with DB.DB(args.db, logger) as db, db.cursor() as cur:
            cur.execute(sql)
            for row in cur: email.append(row[0])
        if email:
            fqdn = socket.getfqdn()
            item = os.path.basename(sys.argv[0])
            cnt = "command line:\n" + ' '.join(sys.argv) + "\n\n"
            cnt+= formatException(exc)
            msg = MIMEText(cnt)
            msg['Subject'] = '{} failed on {}'.format(item, fqdn)
            msg['From'] = email[0]
            msg['To'] = ','.join(email)
            # timeout so a wedged local MTA can't hang the exception handler
            s = smtplib.SMTP('localhost', timeout=30)
            s.send_message(msg)
            s.quit()
    except Exception:
        logger.exception('Exception processing during Notify')
