#! /usr/bin/python2.7
#
# https://imapclient.readthedocs.io/en/stable/
# Also see https://gist.github.com/shimofuri/4348943 for use of idle
#

import ConfigParser
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

import crypto_helpers
from spam import Spam

project = 'SpamMon'
loopforever = True

if os.name == 'nt':
    upath = os.path.join(os.environ['HOMEDRIVE'], os.environ['HOMEPATH'])
    INI_file = os.path.os.path.join(upath, project + '.conf')
    LOG_file = os.path.os.path.join(upath, project + '.log')
else:
    INI_file = '/conf/' + project + '.conf'
    LOG_file = '/var/log/' + project + '.log'
spamDB = Spam()


# imapclient = eventlet.import_patched('imapclient')


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
    for loc in os.curdir, os.path.expanduser('~').join('.' + project), os.path.expanduser('~'), \
               '/etc/' + project, os.environ.get(project + '_CONF'):
        try:
            with open(os.path.join(loc, f), 'r+') as config_file:
                config_ = ConfigParser.SafeConfigParser()
                config_.readfp(config_file)
                break
        except IOError:
            pass
    if config_ is None:
        log.critical('configuration file is missing')
    return config_


# Open config file
config = open_config(INI_file)
f = crypto_helpers.AEScipher()


def exit_gracefully(signum, frame):
    p1.terminate()
    p2.terminate()
    spamDB.close()
    log.info('%s - script stopped...' % 'Main')
    sys.exit(0)


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
    except ConfigParser.NoOptionError:
        log.critical('no "host" option in configuration')
        return
    # retrieve the port
    try:
        PORT = config.get('smtp', 'port')
    except ConfigParser.NoOptionError:
        log.critical('no "port" option in configuration')
        return
    # retrieve the sender
    try:
        SENDER = config.get('smtp', 'sender')
    except ConfigParser.NoOptionError:
        log.critical('no "sender" option in configuration')
        return
    # retrieve the USERNAME
    try:
        USERNAME = config.get('smtp', 'username')
    except ConfigParser.NoOptionError:
        log.critical('no "username" option in configuration')
        return

    # retrieve the PASSWORD
    try:
        PASSWORD = config.get('smtp', 'password')
    except ConfigParser.NoOptionError:
        log.critical('no "password" option in configuration')
        return

    # retrieve the ssl flag
    try:
        SSL = config.get('smtp', 'ssl')
    except ConfigParser.NoOptionError:
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
        conn.login(USERNAME, f.decrypt(PASSWORD))

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
        server_.select_folder('INBOX.Spam')
        messages = server_.search(['UNSEEN'])
    except:
        return

    # fetch new blocked addresses and store them into the dictionary
    for msg in messages:
        try:
            fetch = server_.fetch(msg, ['RFC822'])
            mail = email.message_from_string(
                fetch[msg]['RFC822']
            )
            addr, addrfrom = parseaddr(mail['from'])

            if not spam_.exist(addrfrom):
                spam_.add(addrfrom)
                log.info('New spam address added {0}'.format(addrfrom))
                server_.add_flags(msg, ['\SEEN'])
        except:
            pass


def ScanToRemoveAddresses(server_, spam_):
    # Select the Spam folder to retrieve new spam addresses
    try:
        server_.select_folder('INBOX.NotSpam')
        messages = server_.search()

        # fetch blocked addresses to remove from the list
        for msg in messages:
            fetch = server_.fetch(msg, ['RFC822'])
            mail = email.message_from_string(
                fetch[msg]['RFC822']
            )
            addr, addrfrom = parseaddr(mail['from'])
            if spam_.exist(addrfrom):
                spam_.remove(addrfrom)
                log.info('Address removed from Spam List {0}'.format(addrfrom))
                server_.remove_flags(msg, ['\SEEN'])
                server_.copy(msg, 'INBOX')
                # and delete it from the current folder
                server_.delete_messages(msg)
    except Exception:
        log.critical('Folder INBOX.NotSpam does not exist!')


def mail_monitor(mail_profile):

    global loopforever

    log.info('%s - ... script started' % mail_profile)
    
    while loopforever:
        # <--- Start configuration script

        # Retrieve global params
        try:
            loopvalue = config.get('global', 'loopforever')

        except ConfigParser.NoOptionError:
            log.critical('[global] - no "loopforever" option in configuration')
            return
        except ConfigParser.NoSectionError:
            log.critical('no [global] section in configuration')
            return

        # retrieve the HOST name
        try:
            HOST = config.get(mail_profile, 'host')
        except ConfigParser.NoOptionError:
            log.critical('%s - no "host" option in configuration' % mail_profile)
            return
        except ConfigParser.NoSectionError:
            log.critical('%s - no %s section in configuration' % mail_profile)
            return

        # retrieve the USERNAME
        try:
            USERNAME = config.get(mail_profile, 'username')
        except ConfigParser.NoOptionError:
            log.critical('%s - no "username" option in configuration' % mail_profile)
            return

        # retrieve the PASSWORD
        try:
            PASSWORD = f.read_pwd(INI_file, mail_profile)
        except ConfigParser.NoOptionError:
            log.critical('%s - no "password" option in configuration' % mail_profile)
            return

        # retrieve the cacert.pem file - it is needed under Windows
        try:
            cafile = config.get(mail_profile, 'cafile')
        except ConfigParser.NoOptionError:
            log.warning('%s - no "cafile" option in configuration' % mail_profile)
            cafile = None

        try:
            timeout = config.get(mail_profile, 'timeout')
            nrhours = int(timeout) / 3600 + 1
        except ConfigParser.NoOptionError:
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
                server.select_folder('INBOX')
                # Reads now all INBOX's unseen messages. Should errors occur due to loss of connection,
                # attempt restablishing connection

                mydate = datetime.datetime.now() - datetime.timedelta(hours=nrhours)
                messages = server.search([u'UNSEEN', u'SINCE', mydate])

            except Exception:
                continue

            for msg in messages:
                try:
                    fetch = server.fetch(msg, ['RFC822'])
                    mail = email.message_from_string(
                        fetch[msg]['RFC822']
                    )
                except Exception:
                    continue

                addr, addrfrom = parseaddr(mail['from'])
                if spamDB.exist(addrfrom):
                    # if the mail address exists in the spam list, then move the spam to the Spam folder
                    log.info("%s - %s is a spam" % (mail_profile, addrfrom))
                    server.copy(msg, 'INBOX.Spam')
                    # and delete it from the INBOX
                    server.delete_messages(msg)
                else:
                    server.remove_flags(msg, ['\SEEN'])
                    # do nothing else for non blocked mails
                    # log.info("%s is a mail with subject %s" % (addrfrom, mail['subject']))

            # Check the Spam address list and save it back to file
            ScanForNewSpamAddresses(server, spamDB)
            if loopvalue == 'True':
                log.info('%s - Start monitoring INBOX' % mail_profile)

            if loopvalue != 'True':
                loopforever = False
                
            while loopforever:
                # <--- Start of the forever monitoring loop


                try:
                    # select the folder to monitor
                    server.select_folder('INBOX')
    
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
                    messages = server.search([u'UNSEEN', u'SINCE', mydate])

                    for msg in messages:
                        try:
                            fetch = server.fetch(msg, ['RFC822'])
                            mail = email.message_from_string(
                                fetch[msg]['RFC822']
                            )
                        except Exception:
                            continue

                        addr, addrfrom = parseaddr(mail['from'])

                        # if the mail address exists in the spam list, then move the spam to the Spam folder
                        if spamDB.exist(addrfrom):
                            log.info("%s - %s is a spam " % (mail_profile, addrfrom))
                            server.copy(msg, 'INBOX.Spam')
                            # and delete it from the INBOX
                            server.delete_messages(msg)
                        else:
                            server.remove_flags(msg, ['\SEEN'])
                            # Handle special request as command string in the message subject
                            # log.info("%s is a mail with subject %s" % (addrfrom, mail['subject']))
                            txt = mail['subject']
                            try:
                                if txt.split(' ')[0] == "$SENDLOG":
                                    with open(LOG_file, 'r') as logfile:
                                        log.info('Sending log file to %s' % addrfrom)
                                        server.add_flags(msg, ['\SEEN'])
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
    os.kill(os.getpid(), signal.SIGTERM)
    return


def main():
    global p1, p2

    p1 = multiprocessing.Process(target=mail_monitor, args=('xavier',))
    p1.start()

    p2 = multiprocessing.Process(target=mail_monitor, args=('joelle',))
    p2.start()
    
    signal.signal(signal.SIGINT, exit_gracefully)
    signal.signal(signal.SIGTERM, exit_gracefully)
    

if __name__ == "__main__":
    main()
