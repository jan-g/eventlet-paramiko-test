__author__ = 'jang@ioctl.org'
import eventlet
import eventlet.debug

# Still not sure how some of these FDs get invalidated.
# I'm pretty sure GC is not involved.
import gc
print "gc enabled?", gc.isenabled()

eventlet.monkey_patch()
#eventlet.debug.hub_listener_stacks(True)
#eventlet.debug.hub_timer_stacks(True)
#eventlet.debug.hub_exceptions(True)
# eventlet.debug.spew()

import threading
import thread
import paramiko
import traceback
import sys
import logging
from gettext import gettext as _

logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.WARN) # Or debug
LOG = logging.getLogger(__name__)
CONNECTION_TIMEOUT = 30

_mutex = threading.Lock()
_count = 0

def count():
    global _count
    with _mutex:
        _count += 1

def main(host, user, keyfile):

    connection = Connection(host, user, keyfile=keyfile)
    threads = [ threading.Thread(target = n_times, args = (10, once, connection)) for _ in xrange(10) ]
    for i in threads:
        print "is", i, "a daemon?", i.daemon # I hope not.
        i.start()
    for i in threads:
        i.join()
    print "All done, count is", _count

def n_times(n, callable, *args, **kwargs):
    for _ in xrange(n):
        try:
            callable(*args, **kwargs)
            count()
        except Exception as e:
            print("***n_times catches an exception, %r" % e)

def once(connection):
    client = None
    try:
        # Use paramiko Client to negotiate SSH2 across the connection
        print('*** Connecting...')
        client = ssh_connect(connection)
        print(repr(client.get_transport()))

        print('*** Here we go!\n')
        stdin, stdout, stderr = client.exec_command("ls -l")
        stdin.close()
        for line in stdout:
            print "STDOUT(%s)>" % thread.get_ident(), line.rstrip()
        stdout.close()
        for line in stderr:
            print "STDERR(%s)>" % thread.get_ident(), line.rstrip()
        stderr.close()
        client.close()
        print('*** Closed...')

    except Exception as e:
        print('*** Caught exception: %s: %s' % (e.__class__, e))
        traceback.print_exc()
        try:
            print('*** closing...')
            if client is not None:
                client.close()
        except Exception as e2:
            print('*** Caught close exception: %s: %s' % (e2.__class__, e2))
        raise e


class Connection(object):
    def __init__(self, host, username, password=None, port=22, keyfile=None):
        self.host = host
        self.username = username
        self.password = password
        self.port = port
        self.keyfile = keyfile


class ConnectionFailed(IOError):
    pass

def ssh_connect(connection):
    """Method to connect to remote system using ssh protocol.

    :param connection: a Connection object.
    :returns: paramiko.SSHClient -- an active ssh connection.
    :raises: ConnectionFailed
    """
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(connection.host,
                    username=connection.username,
                    password=connection.password,
                    port=connection.port,
                    key_filename=connection.keyfile,
                    timeout=CONNECTION_TIMEOUT)

        LOG.debug("SSH connection with %s established successfully." %
                  connection.host)

        # send TCP keepalive packets every 20 seconds
        ssh.get_transport().set_keepalive(20)

        return ssh
    except Exception as e:
        LOG.exception(_('Connection error: %s: %s' % (e.__class__, e)))
        traceback.print_exc()
        raise ConnectionFailed()


if __name__ == '__main__':
    try:
        # Usage: para.py localhost $USER ~/.ssh/id_rsa
        main(*sys.argv[1:])
    except:
        print "Hubs remaining listeners:"
        eventlet.debug.format_hub_listeners()
        print "Hubs remaining timers:"
        eventlet.debug.format_hub_timers()
