#!/usr/bin/python
import sys          as _sys
import subprocess   as _proc
import os           as _os
import signal       as _signal
import traceback    as _tb
import time         as _time
import logging      as _log
import signal       as _signal

from logging        import info, warn, error, exception

_IN_DEV     = 'plughw:1,0'
_OUT_DEV    = 'ue'
_CMD        = 'arecord -B 20000 -D %s -f dat | aplay -B 20000 -D %s' % (_IN_DEV, _OUT_DEV)
_SLEEP_SECS = 15
_HIBERNATE_SECS = 3600 * 4


# patterns that we need to be on the lookout for
_KILL_MSG_PATTERNS = [
    # bluetooth disconnect
    'Resource temporarily unavailable'
]

class PipeError(Exception) :
    def __init__(self, msg) :
        Exception.__init__(self, msg)

class Sleeper(object) :
    def __init__(self) :
        self.sleep_secs = _SLEEP_SECS
    def set_hibernate(self) :
        self.sleep_secs = _HIBERNATE_SECS
    def sleep(self) :
        info('Sleeping %d seconds before restarting...', self.sleep_secs)
        _time.sleep(self.sleep_secs)
        self.sleep_secs = _SLEEP_SECS


def main() :
    sleeper = Sleeper()
    while True :
        info('Starting Audio Pipe: %s', _CMD)
        try :
            p = _proc.Popen(args = _CMD, shell = True, stderr = _proc.PIPE, preexec_fn = _os.setsid)

            def hibernate_signal(signum, frame) :
                sleeper.set_hibernate()
                try :
                    _os.killpg(p.pid, _signal.SIGTERM)
                except :
                    # don't worry if this fails
                    pass
            _signal.signal(_signal.SIGUSR1, hibernate_signal)

            # read from stderr and 'tee' it out, intercepting useful info
            while True :
                msg = p.stderr.readline()
                if msg == '' :
                    p.wait()
                    raise PipeError, 'Process terminated'
                _sys.stderr.write(msg)
                for pat_str in _KILL_MSG_PATTERNS :
                    if pat_str in msg :
                        # problem -- we need to terminate the process tree
                        _os.killpg(p.pid, _signal.SIGTERM)
                        # get the status code
                        p.wait()
                        raise PipeError, 'Terminate process due to detected error'
        except :
            exception('Pipe failed.')
        sleeper.sleep()

if __name__ == '__main__' :
    _log.basicConfig(level = _log.INFO, format = '%(asctime)s [%(levelname)-8s] %(message)s')
    main()
