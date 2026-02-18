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

def onException(args:argparse.ArgumentParser, logger:logging.Logger) -> None:
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
            cnt = "command line:\n" + ' '.join(sys.argv)
            cnt+= traceback.format_exc()
            msg = MIMEText(cnt)
            msg['Subject'] = '{} failed on {}'.format(item, fqdn)
            msg['From'] = email[0]
            msg['To'] = ','.join(email)
            s = smtplib.SMTP('localhost')
            s.send_message(msg)
            s.quit()
    except Exception:
        logger.exception('Exception processing during Notify')
