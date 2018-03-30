#! /usr/bin/python2.7
#
# https://imapclient.readthedocs.io/en/stable/
# Also see https://gist.github.com/shimofuri/4348943 for use of idle
#
# http://nas.local:81/phpMyAdmin/
#

import configparser
import datetime
import email
import logging
import multiprocessing
import os
import signal
import ssl
import sys
import traceback
from email.utils import parseaddr
from logging.handlers import RotatingFileHandler
from smtplib import SMTP, SMTP_SSL
from time import sleep

import imapclient
import requests
from imapclient import SEEN
from sqlalchemy import Column, String
from sqlalchemy import create_engine
from sqlalchemy import exc as sqlError
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

project = 'SpamMon'
loopforever = True


if os.name == 'nt':
    INI_file = project + '.conf'
    LOG_file = project + '.log'
else:
    INI_file = '/conf/' + project + '.conf'
    LOG_file = '/var/log/' + project + '.log'


def open_log(name):
    # Setup the log handlers to stdout and file.
    log_ = logging.getLogger(name)
    log_.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        '%(asctime)s | %(name)s | %(levelname)s | %(message)s'
    )
    handler_stdout = logging.StreamHandler(sys.stdout)
    handler_stdout.setLevel(logging.DEBUG)
    handler_stdout.setFormatter(formatter)
    log_.addHandler(handler_stdout)
    handler_file = RotatingFileHandler(
        LOG_file,
        mode='a',
        maxBytes=200000,
        backupCount=9,
        encoding='UTF-8',
        delay=True
    )
    handler_file.setLevel(logging.DEBUG)
    handler_file.setFormatter(formatter)
    log_.addHandler(handler_file)
    return log_


log = open_log(project)


def open_config(f):
    log = open_log(project + '.open_config')
    # Read config file - halt script on failure
    config_ = None
    try:
        with open(f, 'r+') as config_file:
            config_ = configparser.ConfigParser()
            config_.read_file(config_file)
    except IOError:
        pass
    if config_ is None:
        log.critical('configuration file is missing')
    return config_


# Open config file
config = open_config(INI_file)


def get_vault(uid):
    url = config.get('vault', 'vault_url')
    r = requests.get(url=url + '?uid=%s' % uid)
    id = r.json()
    r.close()
    if id['status'] == 200:
        _username = id['username']
        _password = id['password']
    else:
        _username = ''
        _password = ''
    return _username, _password


Base = declarative_base()


class SpamItem(Base):
    __tablename__ = 'spam'
    address = Column(String, primary_key=True)


def init_engine(dbms='mysql'):
    if dbms == 'mysql':
        uid = config.get('mysql', 'uid')
        host = config.get('mysql', 'host')
        db = config.get('mysql', 'db')
        u, p = get_vault(uid)
        s = 'mysql+pymysql://' + u + ':' + p + '@' + host + '/' + db
    else:
        db = config.get('db', 'db')
        s = 'sqlite:///' + db
    
    return create_engine(s)


def create_table(e):
    Base.metadata.create_all(e)


def init_db_session(e):
    Base.metadata.bind = e
    DBsession = sessionmaker()
    DBsession.bind = e
    return DBsession()


class Spam(object):
    
    def __init__(self):
        # Connect to the database
        try:
            self.engine = init_engine()
            self.sql = init_db_session(self.engine)
            self.__status = ''
            log.info('Connected to Spam DB')
        except sqlError.SQLAlchemyError:
            log.error('Cannot initiate connection to database')
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.sql.close()
    
    def __enter__(self):
        return self
    
    def add(self, address):
        # Add a new record
        try:
            self.sql.add(SpamItem(address=address))
            self.sql.commit()
            return True
        except sqlError.SQLAlchemyError:
            log.error('Cannot add an item into the database')
            return False
    
    def remove(self, address):
        # delete a record
        try:
            row = self.sql.query(SpamItem).filter(SpamItem.address == address).first()
            if row is not None:
                self.sql.delete(row)
                self.sql.commit()
                return True
            else:
                log.error('Item %s not found' % address)
                return False
        except sqlError.SQLAlchemyError:
            log.error('Cannot delete an item from the database')
            return False
    
    def exist(self, address):
        try:
            domain = '*@' + address.split('@')[1]
            row = self.sql.query(SpamItem).filter(SpamItem.address == domain).first()
            if row is not None:
                return True
        except IndexError:
            pass
        
        try:
            row = self.sql.query(SpamItem).filter(SpamItem.address == address).first()
            if row is not None:
                return True
            else:
                return False
        except sqlError.SQLAlchemyError:
            return False
    
    def close(self):
        self.sql.close()
    
    def configure(self):
        create_table(self.engine)
    
    @property
    def status(self):
        return self.__status
    
    @status.setter
    def status(self, value):
        raise Exception('Status is a read only property')


spamDB = Spam()


def SendMail(address, subject, content):
    """

    :param address:
    :param subject:
    :param content:
    :return:

    See http://stackoverflow.com/questions/3362600/how-to-send-email-attachments-with-python
    """
    # retrieve the HOST name

    try:
        HOST = config.get('smtp', 'host')
    except configparser.NoOptionError:
        log.critical('no "host" option in configuration')
        return
    # retrieve the port
    try:
        PORT = config.get('smtp', 'port')
    except configparser.NoOptionError:
        log.critical('no "port" option in configuration')
        return
    # retrieve the sender
    try:
        SENDER = config.get('smtp', 'sender')
    except configparser.NoOptionError:
        log.critical('no "sender" option in configuration')
        return

    # retrieve the USERNAME & PASSWORD
    try:
        USERNAME, PASSWORD = get_vault(config.get('smtp', 'uid'))
    except:
        log.critical('%s - no "uid" option in [smtp] section')
        return

    # retrieve the ssl flag
    try:
        SSL = config.get('smtp', 'ssl')
    except configparser.NoOptionError:
        SSL = False

    try:
        if SSL:
            conn = SMTP_SSL(HOST, PORT)
            conn.ehlo()
        else:
            conn = SMTP()
            conn.connect(HOST, PORT)
            conn.ehlo()
            conn.starttls()
            conn.ehlo()

        conn.set_debuglevel(False)
        conn.login(USERNAME, PASSWORD)

        msg = "\r\n".join([
            "From: %s" % SENDER,
            "To: %s" % address,
            "Subject: %s" % subject,
            "",
            content])
        conn.sendmail(SENDER, address, msg)
        conn.close()
    except Exception:
        log.critical('Couldn''t send mail: %s' % subject)


def ScanForNewSpamAddresses(server_, spam_):
    # Select the Spam folder to retrieve new spam addresses
    try:
        server_.select_folder(r'INBOX.Spam')
        messages = server_.search()
    except:
        return

    # fetch new blocked addresses and store them into the dictionary
    for msg in messages:
        try:
            fetch = server_.fetch(msg, [b'RFC822'])
            try:
                mail = email.message_from_bytes(
                    fetch[msg][b'RFC822']
                )
            except:
                mail = email.message_from_string(
                    fetch[msg][b'RFC822']
                )

            addr, addrfrom = parseaddr(mail['from'])

            if not spam_.exist(addrfrom):
                spam_.add(addrfrom)
                log.info('New spam address added {0}'.format(addrfrom))
            server_.copy(msg, r'INBOX.Unwanted')
            server_.delete_messages(msg, True)
        except:
            pass


def ScanToRemoveAddresses(server_, spam_):
    # Select the Spam folder to retrieve new spam addresses
    try:
        server_.select_folder('INBOX.NotSpam')
        messages = server_.search()

        # fetch blocked addresses to remove from the list
        for msg in messages:
            fetch = server_.fetch(msg, [b'RFC822'])
            mail = email.message_from_bytes(
                fetch[msg][b'RFC822']
            )
            addr, addrfrom = parseaddr(mail['from'])
            if spam_.exist(addrfrom):
                spam_.remove(addrfrom)
                log.info('Address removed from Spam List {0}'.format(addrfrom))
                server_.remove_flags(msg, [SEEN])
                server_.copy(msg, 'INBOX')
                # and delete it from the current folder
                server_.delete_messages(msg)
    except Exception:
        log.critical('Folder INBOX.NotSpam does not exist!')


def mail_monitor(mail_profile):

    global loopforever

    log.info('%s - ... script started' % mail_profile)
    signal.signal(signal.SIGINT, exit_gracefully)
    signal.signal(signal.SIGTERM, exit_gracefully)
    
    while loopforever:
        # <--- Start configuration script

        # Retrieve global params
        try:
            if config.get('global', 'debug') == 'True':
                debug = True
            else:
                debug = False

        except configparser.NoOptionError:
            debug = False
            return

        try:
            if not debug:
                if config.get('global', 'loopforever') == 'True':
                    loopvalue = True
                else:
                    loopvalue = False
            else:
                loopvalue = False

        except configparser.NoOptionError:
            log.critical('[global] - no "loopforever" option in configuration')
            return
        except configparser.NoSectionError:
            log.critical('no [global] section in configuration')
            return

        # retrieve the HOST name
        try:
            HOST = config.get(mail_profile, 'host')
        except configparser.NoOptionError:
            log.critical('%s - no "host" option in configuration' % mail_profile)
            return
        except configparser.NoSectionError:
            log.critical('%s - no %s section in configuration' % mail_profile)
            return

        # retrieve the USERNAME & PASSWORD
        try:
            USERNAME, PASSWORD = get_vault(config.get(mail_profile, 'uid'))
        except:
            log.critical('%s - no "uid" option in configuration' % mail_profile)
            return

        # retrieve the cacert.pem file - it is needed under Windows
        try:
            cafile = config.get(mail_profile, 'cafile')
            if os.name == 'nt':
                cafile = cafile.split('/')[2]
        except configparser.NoOptionError:
            log.warning('%s - no "cafile" option in configuration' % mail_profile)
            cafile = None

        try:
            timeout = config.get(mail_profile, 'timeout')
            nrhours = int(timeout) / 3600 + 1
        except configparser.NoOptionError:
            timeout = 300
            nrhours = 1

        while loopforever:
            # <--- start of the IMAP server connection loop

            # attempt connection to the IMAP server
            try:
    
                context = ssl.create_default_context(cafile=cafile)
                # create the connection with the email server
                server = imapclient.IMAPClient(HOST, use_uid=True, ssl=True, ssl_context=context)

            except imapclient.IMAPClient.Error:

                # If connection attempt to IMAP server fails, retry
                etype, evalue = sys.exc_info()[:2]
                estr = traceback.format_exception_only(etype, evalue)
                logstr = '%s - failed to connect to IMAP server - ' % mail_profile
                for each in estr:
                    logstr += '{0}; '.format(each.strip('\n'))
                log.error(logstr)
                sleep(30)
                continue
            log.info('%s - server connection established' % mail_profile)

            # attempt to login to IMAP server
            try:
                # server = IMAPClient(HOST, use_uid=True, ssl=False)
                result = server.login(USERNAME, PASSWORD)
                log.info('%s - login successful - %s' % (mail_profile, result))

            except imapclient.IMAPClient.Error:
                # Halt script when login fails
                etype, evalue = sys.exc_info()[:2]
                estr = traceback.format_exception_only(etype, evalue)
                logstr = '%s - failed to login to IMAP server - ' % mail_profile
                for each in estr:
                    logstr += '{0}; '.format(each.strip('\n'))
                log.critical(logstr)
                break

            try:
                ScanToRemoveAddresses(server, spamDB)
                # Select the INBOX folder for monitoring
                server.select_folder(r'INBOX')
                # Reads now all INBOX's unseen messages. Should errors occur due to loss of connection,
                # attempt restablishing connection

                mydate = (datetime.datetime.now() - datetime.timedelta(hours=24))
                messages = server.search([u'SINCE', mydate])

            except Exception:
                continue

            for msg in messages:
                try:
                    fetch = server.fetch(msg, [b'RFC822'])
                    s = fetch[msg][b'RFC822']
                    mail = email.message_from_bytes(s)
                except Exception as e:
                    print(e)
                    continue

                addr, addrfrom = parseaddr(mail['from'])
                if spamDB.exist(addrfrom):
                    # if the mail address exists in the spam list, then move the spam to the Spam folder
                    log.info("%s - %s is a spam" % (mail_profile, addrfrom))
                    server.copy(msg, 'INBOX.Spam')
                    # and delete it from the INBOX
                    server.delete_messages(msg)
                else:
                    server.remove_flags(msg, [SEEN])
                    # do nothing else for non blocked mails
                    # log.info("%s is a mail with subject %s" % (addrfrom, mail['subject']))

            # Check the Spam address list and save it back to file
            ScanForNewSpamAddresses(server, spamDB)
            if loopvalue:
                log.info('%s - Start monitoring INBOX' % mail_profile)

            if not loopvalue:
                loopforever = False
                
            while loopforever:
                # <--- Start of the forever monitoring loop


                try:
                    # select the folder to monitor
                    server.select_folder(u'INBOX')
    
                    # After all unread emails are cleared on initial login, start
                    # monitoring the folder for new email arrivals and process
                    # accordingly. Use the IDLE check combined with occassional NOOP
                    # to refresh. Should errors occur in this loop (due to loss of
                    # connection), return control to IMAP server connection loop to
                    # attempt restablishing connection instead of halting script.
    
                    server.idle()
                    result = server.idle_check(int(timeout))

                except Exception:
                    continue
                    
                if result:
                    try:
                        server.idle_done()
                    except Exception:
                        continue

                    mydate = datetime.datetime.now() - datetime.timedelta(hours=nrhours)
                    messages = server.search([u'SINCE', mydate])

                    for msg in messages:
                        try:
                            fetch = server.fetch(msg, [b'RFC822'])
                            mail = email.message_from_bytes(
                                fetch[msg][b'RFC822']
                            )
                        except Exception:
                            continue

                        addr, addrfrom = parseaddr(mail[u'from'])

                        # if the mail address exists in the spam list, then move the spam to the Spam folder
                        if spamDB.exist(addrfrom):
                            log.info("%s - %s is a spam " % (mail_profile, addrfrom))
                            server.copy(msg, 'INBOX.Spam')
                            # and delete it from the INBOX
                            server.delete_messages(msg)
                        else:
                            server.remove_flags(msg, [SEEN])
                            # Handle special request as command string in the message subject
                            # log.info("%s is a mail with subject %s" % (addrfrom, mail['subject']))
                            txt = mail['subject']
                            try:
                                if txt.split(' ')[0] == "$SENDLOG":
                                    with open(LOG_file, 'r') as logfile:
                                        log.info('Sending log file to %s' % addrfrom)
                                        server.add_flags(msg, [SEEN])
                                        txt = logfile.read()
                                        SendMail(addrfrom, 'Log file', txt)
                                        server.delete_messages(msg)
                            except Exception:
                                pass

                    # Check the Spam address list and save it back to file
                    ScanForNewSpamAddresses(server, spamDB)

                else:
                    try:
                        server.idle_done()
                        server.noop()
                    except Exception:
                        pass

                # End of monitoring loop --->
                continue

            # end of the IMAP connection loop --->
            # logout
            server.logout()
            break

        # end of configuration section --->
        break

    log.info('%s - script stopped...' % mail_profile)
    # os.kill(os.getpid(), signal.SIGTERM)
    return


p1 = multiprocessing.Process(target=mail_monitor, args=('xavier',))
p2 = multiprocessing.Process(target=mail_monitor, args=('joelle',))


def exit_gracefully(signum, frame):
    global p1, p2
    log.info('%s - script stopped...' % 'Main')
    try:
        p1.terminate()
        p2.terminate()
    except:
        pass
    spamDB.close()
    
    sys.exit(0)


def testspam():
    with Spam() as s:
        s.configure()
        if s.status == '':
            if not s.add("www@ads.com"):
                print('duplicate')
            if s.exist("www@ads.com"):
                print('found')
                if s.remove("www@ads.com"):
                    print('removed')


def main():
    global p1, p2

    if config.get('global', 'loopforever') == 'True':
        p1.start()
        p2.start()
        signal.signal(signal.SIGINT, exit_gracefully)
        signal.signal(signal.SIGTERM, exit_gracefully)
    else:
        mail_monitor('xavier')
        mail_monitor('joelle')
    

if __name__ == "__main__":
    main()
