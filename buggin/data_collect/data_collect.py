import sys
import argparse
import os
from utils import git
from utils.bug_track_obj import NewFunction
import difflib
import re
from utils.jira import JiraAPI
import time
from datetime import datetime
import csv
from syntax_parser import parser_runner


def run_parser(f, log_dir, language):
    f = os.path.abspath(f)
    output_file = log_dir + '/json/'
    if not os.path.isdir(output_file):
        os.makedirs(output_file)
    output_file += os.path.basename(f) + '.json'
    return parser_runner.get_parsed_json(f, output_file, language)


def get_lines_changed(prev_json, new_json):
    d = difflib.Differ()
    diff = d.compare(new_json, prev_json)
    added_reg = re.compile(r'^\+(.*)')
    subtracted_reg = re.compile('^\-(.*)')
    diff = '\n'.join(diff)
    added_arr = filter(lambda x: added_reg.match(x), diff)
    subtracted_arr = filter(lambda x: subtracted_reg.match(x), diff)

    return [len(subtracted_arr), len(added_arr)]


def get_head_info(file_path, head_commit, log_dir, language):
    output_file = get_output_file(file_path, log_dir)
    if not git.write_file_from_version(head_commit, file_path, output_file):
        return False
    head_json = run_parser(output_file, log_dir, language)
    return head_json.keys()


def get_head_commit(commits):
    return commits[-1]['hash']


def get_output_file(f, log_dir):
    output_file = log_dir + '/source_files/'
    if not os.path.isdir(output_file):
        os.makedirs(output_file)
    output_file = output_file
    f_name = f.replace('/', '-')
    output_file += '/' + f_name
    return output_file


def get_output_files(f, commit_hash, prev_commit, log_dir, language):
    output_file = get_output_file(f, log_dir)
    git.write_file_from_version(commit_hash, f, output_file)
    curr_json = run_parser(output_file, log_dir, language)
    git.write_file_from_version(prev_commit, f, output_file)
    prev_json = run_parser(output_file, log_dir, language)
    return [curr_json, prev_json]


def generate_data(commits, log_dir, language, jira_api):
    head_commit = get_head_commit(commits)
    head_files = {}
    prev_commit = None
    #key on file_path->func_name
    functions = {}
    for commit in commits:
        commit_hash = commit['hash']
        start_ts = commit['timestamp']
        author = commit['author']
        #TODO BUG FIX SHIT
        is_bug_fix = is_bug_fix_commit(commit['message'], jira_api)
        if prev_commit is not None:
            changed_files = git.get_changed_files(prev_commit, commit_hash)
            for f in changed_files:
                if not f in head_files:
                    head_files[f] = get_head_info(f, head_commit, log_dir, language)
                if head_files[f] is False:
                    continue
                curr_json, prev_json = get_output_files(f, commit_hash, prev_commit, log_dir, language)
                # aggregate all function names so we can get deleted metrics too?
                # or wait we don't care if shit gets deleted?
                # but what if it comes back?
                for func_name in curr_json.keys():
                    key = '%s-%s' % (f, func_name)
                    if func_name not in head_files[f]:
                        continue
                    #print func_name
                    if func_name in prev_json:
                        lines_deleted, lines_added = get_lines_changed(prev_json[func_name], curr_json[func_name])
                        #print 'Deleted %s' % lines_deleted
                        #print 'Added %s' % lines_added
                        #print 'Total %s' % len(curr_json[func_name])
                    else:
                        lines_deleted, lines_added = [0, len(curr_json[func_name])]
                    if lines_deleted == 0 and lines_added == 0:
                        #twasnt touched
                        continue
                    if key not in functions:
                        #we know this is when the function was created
                        functions[key] = NewFunction(func_name, f, start_ts)
                    functions[key].add_datapoint(
                        lines_added,
                        lines_deleted,
                        len(curr_json[func_name]),
                        author,
                        start_ts,
                        is_bug_fix
                    )

        prev_commit = commit_hash
    return functions, head_files


def split_commits(commits, from_date):
    target_ts = time.mktime(datetime.strptime(from_date, "%Y-%m-%d").timetuple())
    commit_split_index = -1
    for i in range(len(commits)):
        if int(commits[i]['timestamp']) > target_ts:
            commit_split_index = i
            break
    return [commits[:commit_split_index], commits[commit_split_index - 1:-1]]


def format_jira_issue(issue):
    match_obj = re.match('([a-zA-Z]+)-?(\d+)', issue)
    if not match_obj:
        raise Exception('this isnt no jira issue')
    return '%s-%s' % (match_obj.group(1).upper(), match_obj.group(2))


def is_bug_fix_ticket(ticket, jira_api):
    if ticket is None:
        return False
    formatted_ticket = format_jira_issue(ticket)
    try:
        issue = jira_api.get_issue(formatted_ticket, 'issuetype')
    except:
        return False
    return issue['fields']['issuetype']['name'] == 'Bug'


def is_bug_fix_commit(message, jira_api):
    issues = re.findall('\\b[a-zA-Z]+-?\d+\\b', message)
    for issue in issues:
        if is_bug_fix_ticket(issue, jira_api):
            return True
    return False


def mark_buggy_functions(functions, head_files, commits, log_dir, language, jira_api):
    # take all commits
    prev_commit = None
    for commit in commits:
        if prev_commit is None:
            prev_commit = commit['hash']
            continue
        if not is_bug_fix_commit(commit['message'], jira_api):
            prev_commit = commit['hash']
            continue
        commit_hash = commit['hash']
        changed_files = git.get_changed_files(prev_commit, commit_hash)
        for f in changed_files:
            if not f in head_files:
                continue
            curr_json, prev_json = get_output_files(f, commit_hash, prev_commit, log_dir, language)
            # aggregate all function names so we can get deleted metrics too?
            # or wait we don't care if shit gets deleted?
            # but what if it comes back?
            for func_name in curr_json.keys():
                key = '%s-%s' % (f, func_name)
                if func_name not in head_files[f] or key not in functions:
                    continue
                if func_name in prev_json:
                    deleted, added = get_lines_changed(prev_json[func_name], curr_json[func_name])
                else:
                    deleted, added = [0, len(curr_json[func_name])]
                if deleted != 0 or added != 0:
                    functions[key].iterate_future_bugs()
        prev_commit = commit_hash


def collect_data(
    repo_dir,
    lang,
    output_csv,
    rel_src,
    start_time,
    split_time,
    jira_api):
    #since we're using this like a log dir
    #we should make this a tmp dir probs
    prev_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    os.chdir(repo_dir)
    #need hash, datets, author_email, commit_msg
    # should be in order of oldest to newest
    commits = git.get_all_commits(start_time, rel_src)
    # make split programmable
    data_commits, validate_commits = split_commits(commits, split_time)
    # get final commit that we want, i.e. jul 1st,
    # then go get all the methods that exist there
    # create dict {file_name:[func_name]}
    # so we can skip total files too hehe
    #{file_path => False | [func_names]}
    functions, head_files = generate_data(data_commits, prev_dir, lang, jira_api)
    mark_buggy_functions(functions, head_files, validate_commits, prev_dir, lang, jira_api)
    data = map(lambda x: x.get_data_vector(), functions.values())
    with open(output_csv, 'w+') as f:
        csv_writer = csv.writer(f)
        first = True
        for datum in data:
            if first:
                csv_writer.writerow(datum.keys())
                first = False
            csv_writer.writerow(datum.values())
    print 'Done!'


def main(argv):
    p = argparse.ArgumentParser(description='Collect repo data', prog='data_collect')
    p.add_argument('-d', '--repo-dir', help='Path to git repo', required=True)
    p.add_argument('-l', '--language', help='Language', required=True)
    p.add_argument('-o', '--output-csv', help='output csv file', required=True)
    p.add_argument('-r', '--relative-src', help='Relative path to source', default='./')
    p.add_argument('-t', '--start-time', help='First commit to consider', default='2015-01-01')
    p.add_argument('-p', '--split-time', help='Split from collecting measures to detecting future bugs', default='2017-07-01')
    p.add_argument('-a', '--jira-api', help='Jira API url', required=True)
    p.add_argument('-t', '--jira-token', help='Jira API token, b64 encode', required=True)
    args = p.parse_args(argv)
    jira_api = JiraAPI(args.jira_token, args.jira_api)
    collect_data(
        args.repo_dir,
        args.language,
        args.output_csv,
        args.relative_src,
        args.start_time,
        args.split_time,
        jira_api
    )
    print 'Done!'

if __name__ == '__main__':
    main(sys.argv[1:])
