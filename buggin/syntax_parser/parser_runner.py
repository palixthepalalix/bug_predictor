import sys
from os import path
from subprocess import call
import json
import argparse

LANGUAGE_TO_EXEC_MAP = {
    'php': '%s/php/php_parser.php -f %s -o %s',
}


def get_parsed_json(file_input, json_output, language):
    if language not in LANGUAGE_TO_EXEC_MAP:
        print '%s is not yet supported by parser' % language
        return False
    root_parser_dir = path.abspath(path.dirname(__file__))
    executable = LANGUAGE_TO_EXEC_MAP[language] % (root_parser_dir, file_input, json_output)
    call(executable, shell=True)
    with open(json_output, 'r') as f:
        j = json.loads(f.read())
        return j if len(j) else {}


def main(argv):
    parser = argparse.ArgumentParser(description='Run syntax parser', prog='parser')
    parser.add_argument('-f', '--input-file', help='Path to file', required=True)
    parser.add_argument('-o', '--output-file', help='Path to output json file', required=True)
    parser.add_argument('-l', '--language', help='Language to parse', required=True)
    args = parser.parse_args(argv)
    get_parsed_json(args.input_file, args.output_file, args.language)
    parsed_json = get_parsed_json(args.input_file, args.output_file, args.language)
    if parsed_json is False:
        exit(1)
    print json.dumps(parsed_json)


if __name__ == '__main__':
    main(sys.argv[1:])
