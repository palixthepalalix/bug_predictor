from subprocess import check_output, call
import re

BRANCH_PATTERN = '^Merge\s(?:(?:remote-tracking\sbranch\s\'[\w]+\/([a-zA-Z]+-?\d+).*\')|(?:pull\srequest.+from\s([a-zA-Z]+-?\d+)[^\s]+\sto\s.+))$'


def get_changed_files(prev_commit, curr_commit):
    changed_files = check_output(['git', 'diff', '--name-only', prev_commit, curr_commit, '--', './src'])
    return changed_files.strip(' \t\n\r').split()


def write_file_from_version(commit, f, output_file):
    with open(output_file, 'w+') as fd:
        return (call(['git', 'show', commit + ':' + f], stdout=fd) == 0)


def get_merge_commits():
    commits = check_output(['git', 'log', '--grep', '^Merge remote-tracking branch', '--grep', '^Merge pull request', '--format=%H %s', '--since=2017-09-01', '--', './src/']).strip(' \t\n\r')
    formatted_commits = []
    for commit in commits.split('\n'):
        split_commit = commit.split(' ', 1)
        match_obj = re.match(BRANCH_PATTERN, split_commit[1])
        if match_obj:
            ticket = match_obj.group(1) if match_obj.group(1) is not None else match_obj.group(2)
        else:
            ticket = None
        formatted_commits.append({'hash': split_commit[0], 'ticket': ticket})
    return formatted_commits


def get_all_commits(start_time, relative_src):
    cmd = [
        'git',
        'log',
        '--format=%H,%ae,%at,%s',
        '--since=%s' % start_time,
        '--',
        relative_src,
    ]
    commits = check_output(cmd).strip(' \t\n\r').split('\n')
    formatted_commits = []
    for commit in reversed(commits):
        split_commit = commit.split(',', 3)
        formatted_commits.append({
            'hash': split_commit[0],
            'author': split_commit[1],
            'timestamp': split_commit[2],
            'message': split_commit[3],
            })
    return formatted_commits


def get_commit_files(commit):
    cmd = [
        'git',
        'show',
        '--pretty=""',
        '--name-only',
        commit,
    ]
    commits = check_output(cmd).strip(' \t\n\r').split('\n')
    return commits
