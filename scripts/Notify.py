#
# Called with an exception and send an email if needed
#
import sys
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
        db = DB.DB(args.db, logger)
        with db.cursor() as cur:
            cur.execute(sql)
            for row in cur: email.append(row[0])
        db.close()
        print(traceback.format_exc())
        return
        if email: 
            fqdn = socket.getfqdn()
            msg = MIMEText(traceback.format_exc())
            msg['Subject'] = '{} failed on {}'.format(sys.argv[0], fqdn)
            msg['From'] = email[0]
            msg['To'] = ','.join(email)
            s = smtplib.SMTP('localhost')
            s.send_message(msg)
            s.quit()
    except Exception as e:
        logger.exception('Exception processing during Notify')
