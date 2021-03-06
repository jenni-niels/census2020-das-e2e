#!/usr/bin/env python3
#
"""
cspark --- tools for running Spark more easily from Python
"""
#
__author__ = "Simson L. Garfinkel"
__version__ = "0.0.1"

import os
import sys
import time
import glob

SPARK_ENV_LOADED = "SPARK_ENV_LOADED"
AWS_PATH = 'AWS_PATH'

LOG4J_ERRORS_TO_CONSOLE = """<?xml version="1.0" encoding="UTF-8" ?>
<!DOCTYPE log4j:configuration SYSTEM "log4j.dtd">

<log4j:configuration xmlns:log4j="http://jakarta.apache.org/log4j/">
   <appender name="console" class="org.apache.log4j.ConsoleAppender">
    <param name="Target" value="System.out"/>
    <layout class="org.apache.log4j.PatternLayout">
    <param name="ConversionPattern" value="%d{yyyy-MM-dd HH:mm:ss} %-5p %c{1}:%L - %m%n" />
    </layout>
  </appender>
    <logger name="org.apache.spark">
        <level value="error" />
    </logger>
    <logger name="org.spark-project">
        <level value="error" />
    </logger>
    <logger name="org.apache.hadoop">
        <level value="error" />
    </logger>
    <logger name="io.netty">
        <level value="error" />
    </logger>
    <logger name="org.apache.zookeeper">
        <level value="error" />
    </logger>
   <logger name="org">
        <level value="error" />
    </logger>
    <root>
        <priority value="error" />
        <appender-ref ref="console" />
    </root>
</log4j:configuration>
"""


# detach:
# loosely based on https://bugs.python.org/file23719/pydaemon.py
# detach frmo the console; write output to a file.
def detach(logdir=os.getcwd()):
    """Redirect stdout and stderr to a file in the current directory, or logdir if specified"""
    #
    # Don't detach if we are running under Spark; we already detached, and Spark may not handle detaching
    if spark_running():
        print("Spark is running; will not detach", file=sys.stderr)
        return

    pid = os.fork()
    if pid == -1:
        raise RuntimeError("Cannot fork")
    if pid > 0:
        # We are the parent. Exit
        os._exit(0)  # do not call any registered signal handlers
    # We are first child. 
    os.setsid()  # become a session leader

    pid = os.fork()  # Fork a second achild and immediately exit to prevent zombies
    if pid == -1:
        raise RuntimeError("Cannot fork 2")
    if pid > 0:
        # We are the second parent
        os._exit(0)
    os.chdir(logdir)
    # Open both stdout and stderr as files
    pid = os.getpid()
    # Make stdout and stderr unbuffered
    # https://stackoverflow.com/questions/107705/disable-output-buffering
    os.environ['PYTHONUNBUFFERED'] = '1'
    stdout = open("{}.stdout".format(pid), "a+")
    stderr = open("{}.stderr".format(pid), "a+")
    os.dup2(stdout.fileno(), sys.stdout.fileno())
    os.dup2(stderr.fileno(), sys.stderr.fileno())
    stdout.close()
    stderr.close()

    # Most daemon implementations close all FDs. But that is not what we want, so just return

def spark_submit_cmd(*, pyfiles=[], pydirs=[], num_executors=None,
                     conf=[], configdict=None, properties_file=None):
    """Make the spark-submit command without the script name or script args"""
    # pyfiles += ["census_etl.zip", "census_etl/ctools.zip", "census_etl/dfxml/python.zip"]
    for dirname in pydirs:
        for pathname in glob.glob(os.path.join(dirname, '*.py')):
            pyfiles.append(pathname)
    print("pyfiles:", pyfiles)
    cmd = ['spark-submit']
    if pyfiles:
        cmd += ['--py-files', ",".join(pyfiles)]
    if num_executors:
        cmd += ['--num-executors', str(num_executors)]
    for c in conf:
        assert '=' in c
        cmd += ['--conf', c]
    for (key, value) in configdict.items():
        cmd += ['--conf', '{}={}'.format(key, value)]
    if properties_file:
        cmd += ['--properties-file', properties_file]
    print("cmd:", cmd)
    return cmd


def spark_running():
    """Return True if we are running inside Spark"""
    return SPARK_ENV_LOADED in os.environ


def spark_available():
    """Returns True if Spark is available"""
    # Right now, only allow Spark on Amazon
    if AWS_PATH not in os.environ:
        return False
    import distutils.spawn
    return distutils.spawn.find_executable("spark-submit") and True


def spark_make_loglevel_file(loglevel="error"):
    # Create a file with the requested log level
    import tempfile
    with tempfile.NamedTemporaryFile(suffix='.xml', delete=False, mode="w") as f:
        f.write(LOG4J_ERRORS_TO_CONSOLE.replace("error", loglevel))
        f.close()
        return f.name


def spark_submit(*, loglevel=None, pyfiles=[], pydirs=[], num_executors=None, conf=[], configdict={},
                 properties_file=None, argv):
    """Provides support for the --spark command. To the caller, it looks
    like we just returned.  At that point, you can then import your pyspark libraries
    and use SparkContext() to get a spark context.
    However, it reruns this program with
    spark-submit. It also takes all files and sends them to the
    executor. So basically, calling spark_submit() in a program engages spark and returns 0 if success and an error code if not.
    @param pyfiles - a list of files that should be added to the --py-files argument
    @param pydirs  - a list of file systme directories; add every .py file in each folder to the --py-files argument
    @param loglevel - if specified, run at this log level
    @param num_executors - The number of executors to use
    @param conf    - a list containing name=value Spark properties to add to the --conf 
    @param properties_file - a file to be added as a --properties_file
    @param configdict - a dictionary of configuration parameters, designed to be taken from the [spark] section of a config.ini file.
    @param argv    - sys.argv (args[0] is script to run; remainder are arguments)
    @return Returns True if Spark was successfully run
    """
    import subprocess
    if spark_running():
        return True             # running inside Spark
    cmd = spark_submit_cmd(pyfiles=pyfiles, pydirs=pydirs, 
                           num_executors=num_executors, conf=conf, 
                           configdict=configdict, properties_file=properties_file)

    if loglevel:
        tfname = spark_make_loglevel_file(loglevel)
        cmd += ['--conf', 'spark.driver.extraJavaOptions=-Dlog4j.configuration=file:'+tfname,
                '--conf', 'spark.executor.extraJavaOptions=-Dlog4j.configuration=file:'+tfname]

    assert type(argv) == list
    cmd += argv

    print("=== RUNNING SPARK ===")
    print("$ pwd")
    print(os.getcwd())
    print("$ {}".format(" ".join(cmd)))
    
    r = subprocess.run(cmd)
    if r.returncode != 0:
        raise RuntimeError("spark-submit failed r={}".format(r))
    return False                # not running inside Spark; it already ran...
    

def spark_context(*,loglevel=None, pyfiles=[],pydirs=[],num_executors=None, conf=[], configdict={},
                  properties_file=None):
    """If spark is running, return the Spark Context.
    If spark is not running, rerun the program under spark and to get to this same point.
    Notice that we find all current python files and add them.
    This should be called early in a program's life, immediately after arguments are parsed
    and before logging is started."""

    if spark_submit(pyfiles=pyfiles, pydirs=pydirs, num_executors=num_executors,
                        conf=conf, configdict=configdict, properties_file=properties_file,
                        argv=sys.argv):
        # Running inside Spark
        from pyspark import SparkConf
        from pyspark import SparkContext
        conf = SparkConf()
        sc = SparkContext(conf=conf)
        
        # for zipfile in zipdirs:
        # need to use zip files or a whole bunch of import statement will be broken
        # SLG: This is not the correct way to do this; the files should be added to pyfiles and pydirs...
        # sc.addPyFile("census_etl.zip")
        # sc.addPyFile("census_etl/ctools.zip")
        # sc.addPyFile("census_etl/dfxml/python.zip")
        return sc
    exit(0)                     # spark-submit successfully submitted, so exit from the caller.


if __name__ == "__main__":
    from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter
    parser = ArgumentParser(formatter_class=ArgumentDefaultsHelpFormatter,
                             description="Demo program for cspark module")
    parser.add_argument('--debug',  action='store_true')
    parser.add_argument("--detach", action="store_true")
    parser.add_argument("--spark",  action="store_true", help="Run a sample program with spark")

    args = parser.parse_args()
    if args.detach:             # must be checked before Spark
        print("Detaching...")
        detach()
        sys.stdout.write("This was written to stdout at {}...\n".format(time.asctime()))
        sys.stderr.write("This was written to stderr...\n")
        time.sleep(600)
        sys.stdout.write("This was written to stdout 600 seconds later at {}...\n".format(time.asctime()))
        sys.stderr.write("This was written to stderr 600 seconds later...\n")
    
    if args.spark:
        sc = spark_context()    # create a Spark context with spark-submit
        import operator
        result = sc.parallelize(range(0, 1000001)).reduce(operator.add)
        print("***********************************")
        print("sum of number 1 to 1000000: {}".format(result))
        print("***********************************")
        assert result == 500000500000
