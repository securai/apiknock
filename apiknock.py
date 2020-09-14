from importlib import reload
from parser.openapi import OpenAPIParser
from parser.swagger import SwaggerParser
from modules.requester import Requester
from modules.knockerconfig import KnockerConfig, USER_COUNT
from modules.junit import JUnitCreator
from optparse import OptionParser
from modules.tester import Tester
import sys
import os
import logging

logger = logging.getLogger('apiknock')

usage = "%prog [options] <api-file>"


def get_parser(file_format):
    if file_format not in ['openapi', 'swagger']:
        raise ValueError("Invalid file format. Can be 'openapi', 'swagger'.")

    if file_format == 'openapi':
        return OpenAPIParser()
    elif file_format == 'swagger':
        return SwaggerParser()


def get_base_url(options, parser):
    base_url = None
    try:
        base_url = parser.get_base_url()
    except ValueError:
        pass

    if options.override_base_url:
        base_url = options.override_base_url

    if base_url:
        msg = "[+] Using base URL: %s" % base_url
        print(msg)
        logger.info(msg)
        return base_url
    else:
        msg = "[E] Could not extract base URL from API spec. Please use --override-base-url."
        print(msg)
        logger.critical(msg)
        sys.exit(1)


def main():
    print(""" _______ _______ _______ _______ __   _ _____ _     _ _______
 |______ |______ |       |_____| | \  |   |   |     | |  |  |
 ______| |______ |_____  |     | |  \_| __|__ |_____| |  |  |
 
 [  knock, knock... I'm there...  -  secanium.de/apiknock   ]                                
    """)
    opt_parser = OptionParser(usage=usage)
    opt_parser.add_option("-f", "--format", dest="format",
                          help="the api file FORMAT (can be swagger)", metavar="FORMAT")
    opt_parser.add_option("-i", "--insecure", action="store_false", dest="verify_certs", default=True,
                          help="ignore certificate warnings (!!INSECURE!!)")
    opt_parser.add_option("-p", "--proxy", dest="proxy", help="specify a PROXY server", metavar="PROXY")
    opt_parser.add_option("-c", "--config", dest="config_filename", help="specify a configuration FILE", metavar="FILE")
    opt_parser.add_option("-g", "--generate-config", metavar="FILENAME", dest="generate_config_filename",
                          help="generate a config file and store it in FILENAME")
    opt_parser.add_option("-l", "--logfile", metavar="FILENAME", dest="logfile", help="write log output to FILE")
    opt_parser.add_option("-d", "--log-level", metavar="LOGLEVEL", dest="loglevel", help="specify LOGLEVEL")
    opt_parser.add_option("-a", "--auth-type", metavar="TYPE", dest="auth_type",
                          help="sets the authentication to TYPE (can be: bearer, header, cookie, query)")
    opt_parser.add_option("-n", "--auth-name", metavar="NAME", dest="auth_name", help="sets the parameter, cookie or "
                                                                                      "header name for authentication")
    opt_parser.add_option("-o", "--out-format", metavar="FORMAT", dest="out_format", help="specifies the output FORMAT"
                                                                                          "can be junit")
    opt_parser.add_option("-w", "--output-file", metavar="FILE", dest="out_file", help="specifies the output FILE")

    opt_parser.add_option("--fire", help="Just send out all requests once", dest="fire", default=False,
                          action="store_true")
    opt_parser.add_option("-u", "--override-base-url", dest="override_base_url", help="overrides defined base URL in "
                                                                                      "spec")

    opt_parser.add_option("-1", "--user-1", metavar="TOKEN", dest="user_1_token", help="TOKEN for user 1")
    opt_parser.add_option("-2", "--user-2", metavar="TOKEN", dest="user_2_token", help="TOKEN for user 2")
    opt_parser.add_option("-3", "--user-3", metavar="TOKEN", dest="user_3_token", help="TOKEN for user 3")
    opt_parser.add_option("-4", "--user-4", metavar="TOKEN", dest="user_4_token", help="TOKEN for user 4")
    opt_parser.add_option("-5", "--user-5", metavar="TOKEN", dest="user_5_token", help="TOKEN for user 5")
    opt_parser.add_option("-6", "--user-6", metavar="TOKEN", dest="user_6_token", help="TOKEN for user 6")
    opt_parser.add_option("-7", "--user-7", metavar="TOKEN", dest="user_7_token", help="TOKEN for user 7")
    opt_parser.add_option("-8", "--user-8", metavar="TOKEN", dest="user_8_token", help="TOKEN for user 8")
    opt_parser.add_option("-9", "--user-9", metavar="TOKEN", dest="user_9_token", help="TOKEN for user 9")

    (options, args) = opt_parser.parse_args()

    if len(args) < 1:
        opt_parser.error('API filename is missing')

    api_file = args[0]
    if not os.path.isfile(api_file):
        opt_parser.error('<api-file> is not a file.')

    file_format = options.format
    if not file_format or file_format not in ['openapi', 'swagger']:
        opt_parser.error('Invalid API file FORMAT. Can be \'openapi\', \'swagger\'.')

    if not options.config_filename and not options.generate_config_filename and not options.fire:
        opt_parser.error('Please provide either a config file (-c) or generate a new one (-g). Or use --fire.')

    if options.logfile:
        # Obviously some of the imported modules messes with the logger configuration. Shame!
        # If those two lines are removed everything is printed out to stdout as well
        logging.shutdown()
        reload(logging)

        if options.loglevel:
            loglevel_dict = {
                'DEBUG': logging.DEBUG,
                'INFO': logging.INFO,
                'WARNING': logging.WARNING,
                'ERROR': logging.ERROR,
                'CRITICAL': logging.CRITICAL
            }
            if options.loglevel.upper() in loglevel_dict:
                if loglevel_dict[options.loglevel.upper()] == logging.DEBUG:
                    print("[W] !WARNING! Debug-Logging will also log ALL YOUR TOKENS!")
                logger.setLevel(loglevel_dict[options.loglevel.upper()])
            else:
                opt_parser.error("Invalid log-level. Can be 'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'.")
        else:
            logger.setLevel(logging.ERROR)
        fh = logging.FileHandler(options.logfile)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        fh.setFormatter(formatter)
        logger.addHandler(fh)

    try:
        parser = get_parser(file_format)
        parser.parse_file(api_file)
    except ValueError as ex:
        print("[E] Error occurred while processing API file: %s" % ex)
        sys.exit(2)

    if options.fire:
        base_url = get_base_url(options, parser)
        req = Requester(
            base_url,
            verify_certs=options.verify_certs,
            proxy=options.proxy,
            auth_type=options.auth_type,
            auth_name=options.auth_name,
            request_list=parser.get_parsed_requests(),
        )

        req.process_all_requests(options.user_1_token)

    if options.generate_config_filename:
        try:
            user_count = int(input("So, tell me. How many users do you want to knock for? "))

            if user_count < 2 or user_count > 9:
                raise ValueError
        except ValueError:
            print("[E] Please provide a valid number of users... Can be between 2 and 9.")
            sys.exit(2)

        config = KnockerConfig()
        config.set(USER_COUNT, user_count)
        config.generate_config_file(parser.get_parsed_requests(), options.generate_config_filename)
        print("[+] Success: Written configuration file to %s." % options.generate_config_filename)
        sys.exit(0)

    if options.out_format or options.out_file:
        if not options.out_format and options.out_file:
            opt_parser.error("Please provide both, output format (-o) and output filename (-w).")

        if options.out_format not in ['junit']:
            opt_parser.error("Pleas provide a valid output format. Can be 'junit'.")

    if options.config_filename:
        if not options.auth_type or not options.user_1_token:
            opt_parser.error("Please provide authentication info (-a, -n, -1, ...")

        knocker_conf = KnockerConfig()
        knocker_conf.load_config_file(options.config_filename)

        user_count = knocker_conf.get(USER_COUNT)

        if user_count < 2 or user_count > 9:
            print("[E] Invalid value of 'user_count' in config file. Can be between 2 and 9.")

        token_dict = {}

        for user_number in range(1, user_count + 1):
            token = getattr(options, 'user_%d_token' % user_number)

            if not token:
                opt_parser.error("There are %d users in config file, but the token for user %d is missing." % (
                    user_count, user_number
                ))

            token_dict['user_%d' % user_number] = token

        base_url = get_base_url(options, parser)
        req = Requester(
            base_url,
            verify_certs=options.verify_certs,
            proxy=options.proxy,
            auth_type=options.auth_type,
            auth_name=options.auth_name,
        )

        tester = Tester(parser.get_parsed_requests(), knocker_conf, req, token_dict)
        tester.test_all_requests()

        if options.out_file:
            junit = JUnitCreator(tester)
            try:
                with open(options.out_file, "w") as out_file:
                    out_file.write(junit.generate_xml())
            except IOError as ex:
                print("[E] Could not write to output file: %s" % str(ex))


if __name__ == '__main__':
    main()
