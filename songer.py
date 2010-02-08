# TODO: modify mp3 metadata

import logging
import optparse
import os
import re

from string import Template
    
USAGE="Usage: %prog [options] in-format [out-format]"
DEFAULT_OUT_FORMAT = "$artist - $track $title.mp3"
# The list of tokens we're prepared to process
NAMES = ["artist", "title", "track"]

RETURN_OK=0
RETURN_ERROR=1
RETURN_USAGE=2

logger = logging.getLogger("songer")

def getParser():
    """
    return: optparse.parser with the appropriate options set
    """
    parser = optparse.OptionParser(usage=USAGE)
    parser.add_option("-d", "--debug",
                      dest="debug",action="store_true",default=False,
                      help="Set loglevel=DEBUG")
    parser.add_option("--dir",
                      dest="dir", action="store", default=".",
                      help="Specify directory to be read. default='%default'")
    parser.add_option("--replace",
                      dest="replacements", action="append",
                      help="Specify a string replacement to be applied to a named token. "
                           "Can be specified more than once.",
                      metavar="tokenName:oldString:newString")
    parser.add_option("--set",
                      dest="setTokens", action="append",
                      help="Specify a specific value for an output token. "
                           "Can be specified more than once.",
                      metavar="tokenName:value")
    return parser

def setupLogger(options):
    if options.debug:
        logLevel = logging.DEBUG
    else:
        logLevel = logging.INFO
    logger.setLevel(logLevel)
    ch = logging.StreamHandler()
    ch.setLevel(logLevel)
    formatter = logging.Formatter("%(asctime)s %(filename)s:%(funcName)s[%(lineno)d]\n%(message)s",
                                  "%H:%M:%S")
    ch.setFormatter(formatter)
    logger.addHandler(ch)

def getFiles(dir='.'):
    """
    Get all the mp3 files in the specified directory.
    
    dir: Directory to glob.
    return: The list of files.
    """
    files = os.listdir(dir)
    logger.debug("raw files = ['%s']"%"' '".join(files))
    files = filter( lambda x : x.lower().endswith(".mp3"), files)
    logger.debug("filtered files = ['%s']"%"' '".join(files))
    return files

def applyUserReplacements(keywordMap, replacements):
    """
    Parses the user-specified replacements and applies them to each keyword value.
    
    keywordMap: dict of token-value pairs
    replacements: list of replacement strings. Each string is of the form "token:oldString:newString"
    return: The updated keyword map
    """
    
    for r in replacements:
        (key, oldString, newString) = r.split(":")
        logger.debug("replacement: '%s', '%s' -> '%s'"%(key, oldString, newString))
        keywordMap[key] = keywordMap[key].replace(oldString, newString)
    return keywordMap
def getInOutPairs(inFiles, inRegexp, outTemplate, replacements=None, setTokens=None):
    """
    Matches each input file against the input regular expression to get keyword-value pairs, then
    substitutes those into each infile.
    
    inFiles: List of input files
    inRegexp: re.regexp to be applied to the input files
    outTemplate: string.Template defining the format of the output files
    replacements: list of replacement strings. Each string is of the form "token:oldString:newString"
    setTokens: list of setToken strings. Each string is of the form "token:value"
    return: list of input file / output file tuples
    """
    results = list()
    for f in inFiles:
        logger.debug("Processing inFile '%s'"%f)
        # Match the infile against the regexp, which gives us the values for our keys
        inMatch = inRegexp.match(f)
        if inMatch is None:
            print "inFile '%s' doesn't match in-format. Skipping."%f
            continue
        keywordMap = dict()
        for n in NAMES:
            # Save each key/value
            keywordMap[n] = inMatch.group(n)
            logger.debug("%s = %s"%(n, keywordMap[n]))
        if setTokens is not None:
            for s in setTokens:
                (token, value) = s.split(":")
                keywordMap[token]=value
        if replacements is not None:
            # Update the keywordMap values with user-specified replacements
            keywordMap = applyUserReplacements(keywordMap, replacements)
        # Come up with the potential output file by substituting in the values for each key
        outFile = outTemplate.substitute(keywordMap)
        logger.debug("inFile '%s' -> outFile '%s'"%(f, outFile))
        # Save the result to display to the user for confirmation
        results.append((f, outFile))
    return results
def getCompiledRegexp(inFormat):
    """
    Converts the input format string to a regular expression which can be matched against a song title.
    
    inFormat: The input format string, like "$artist - $title - $track.mp3"
    return: re.regexp which can be used to match against song titles
    """
    reString = "^"+inFormat+"$"
    reString = reString.replace(".", "\\.")
    for n in NAMES:
        # Rename the variable parts from "$someName" to something identifiable by a regular expression
        reString = reString.replace("$%s"%n, "(?P<%s>.+)"%n)
    logger.debug("inRegexpString = '%s'"%reString)
    return re.compile(reString)
def doChanges(pairs):
    """
    Prints the proposed song title changes, asks the user to confirm them, and acts accordingly.
    
    pairs: list of input file / output file tuples
    return: 0 if changes were made, 1 if no changes were made
    """
    if len(pairs)>0:
        print "Confirm changes:"
        # Get the max inFile length so we can print them in an aligned column
        maxInfileLength = max([len(p[0]) for p in pairs])
        for pair in pairs:
            print "%*s -> '%s'"%(maxInfileLength+2, "'"+pair[0]+"'", pair[1])

        response = raw_input("Rename these files? ('yes' to proceed) ")
        if response.lower() in ['y', 'yes']:
            # Do it!
            for pair in pairs:
                os.rename(*pair)
            print "Files have been renamed."
            return RETURN_OK
        else:
            # Don't do it
            print "No changes made."
            return RETURN_ERROR
    else:
        # Nothing to do
        print "No changes to be made."
        return RETURN_ERROR
def main():
    parser = getParser()
    (options, args) = parser.parse_args()

    setupLogger(options)

    # Get input arguments
    if len(args) not in [1,2]:
        parser.print_usage()
        return RETURN_USAGE
    else:
        inFormat = args[0]
        try:
            outFormat = args[1]  
        except:
            outFormat = DEFAULT_OUT_FORMAT
    logger.debug("inFormat = '%s'"%inFormat)
    logger.debug("outFormat = '%s'"%outFormat)

    # Convert and compile the input pattern
    inRegexp = getCompiledRegexp(inFormat)
    logger.debug("inRegexp = %s"%inRegexp.pattern)

    # Create the output template
    outTemplate = Template(outFormat)
    logger.debug("outTemplate = %s"%outTemplate.template)

    # Get the list of files we're going to rename
    inFiles = getFiles(options.dir)
    logger.debug("inFiles = ['%s']"%"' '".join(inFiles))

    # Come up with a list of infile-outfile pairs
    pairs = getInOutPairs(inFiles, inRegexp, outTemplate, options.replacements, options.setTokens)

    # Print the results and ask for confirmation
    retVal = doChanges(pairs)

    logging.shutdown()
    return retVal

if __name__ == '__main__':
    exit(main())