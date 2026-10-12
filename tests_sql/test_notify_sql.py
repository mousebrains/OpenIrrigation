"""Notify.recipients() against the real emailReports/webList join."""

import Notify


def test_recipients(db):
    cur = db.cursor()
    cur.execute("INSERT INTO usr(name) VALUES('Tester') RETURNING id;")
    usr = cur.fetchone()["id"]
    cur.execute("INSERT INTO email(usr,email) VALUES(%s,'t@example.org') RETURNING id;", (usr,))
    email = cur.fetchone()["id"]
    cur.execute("INSERT INTO emailReports(email,report)"
                " SELECT %s,id FROM webList WHERE grp='reports' AND key='lowFlow';", (email,))
    assert Notify.recipients(cur, 'lowFlow') == ['t@example.org']
    assert Notify.recipients(cur, 'highFlow') == []
