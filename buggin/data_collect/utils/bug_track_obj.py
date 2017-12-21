class MeasureList:

    def __init__(self, num_commits, calc_metric_func, name):
        # LOC
        # Added LOC / TOTAL
        # deleted LOC / TOTAL
        # num times changed? basically 1 or 0? normalized over time? so earlier changes get less weight
        # newer changes weighted more heavily
        # given change metrics, how to compute a score
        self._func = calc_metric_func
        self._values = [0 for i in range(num_commits - 1)]
        self._name = name

    def iterate_metric(self, index, added_lines, del_lines, total, is_bug_fix):
        #call self.func with parameters or some shit
        self._values[index] = self._func(added_lines, del_lines, total, is_bug_fix)

    def summarize(self):
        return self._summarize_func(self._values)

    def get_sum(self):
        return sum(self._values)

    def get_avg(self):
        return sum(self._values) / float(len(self._values))

    def get_max(self):
        return max(self._values)

    def get_name(self):
        return self._name

    def set_sum_rank(self, buckets):
        self._sum_rank = buckets.index(self.get_sum())

    def get_sum_rank(self):
        return self._sum_rank

    #def get_weighted_avg(self):
        #do shit

    def __str__(self):
        return ('%s: AVG %s MAX %s' % (self._name, self.get_avg(), self.get_max()))


def added_vs_total(added_lines, del_lines, total, is_bug_fix):
    #print added_lines
    #print total
    return added_lines / float(total)


def del_vs_total(added_lines, del_lines, total, is_bug_fix):
    return del_lines / float(total)


def num_change(added_lines, del_lines, total, is_bug_fix):
    return 1 if (abs(added_lines) + abs(del_lines) > 0) else 0


def added_vs_deleted(added_lines, del_lines, total, is_bug_fix):
    d = del_lines if del_lines > 0 else 1
    return -(added_lines / float(d))


def add_bug_commit(added_lines, del_lines, total, is_bug_fix):
    return 1 if ((added_lines > 0 or del_lines > 0) and is_bug_fix) else 0


class NewFunction:

    def __init__(self, name, file_path, init_timestamp):
        self._name = name
        self._path = file_path
        self._added = []
        self._deleted = []
        # binary vector, 0 = not bug commit, 1 = bug commit
        self._bugs = []
        self._total_loc = []
        # use this to track number of authors at each touch
        self._uniq_authors = []
        self._num_authors = []
        self._start_age = init_timestamp
        self._last_touched = init_timestamp
        self._future_bugs = 0

    def add_datapoint(self, added, deleted, new_total, author, commit_ts, is_bug_fix):
        self._added.append(added)
        self._deleted.append(deleted)
        if new_total == 0:
            print added
            print deleted
            print self._name
        self._total_loc.append(new_total)
        if author not in self._uniq_authors:
            self._uniq_authors.append(author)
        self._num_authors.append(len(self._uniq_authors))
        self._last_touched = commit_ts
        self._bugs.append(1 if is_bug_fix else 0)

    def get_max_ratio(self, values1, values2):
        curr_max = -1
        for i in range(len(values1)):
            v = self.get_ratio(values1[i], values2[i])
            if v > curr_max:
                curr_max = v
        return curr_max

    def get_avg_ratio(self, values1, values2):
        ratio_values = []
        for i in range(len(values1)):
            ratio_values.append(self.get_ratio(values1[i], values2[i]))
        return sum(ratio_values) / float(len(ratio_values))

    def get_ratio(self, v1, v2):
        div_val = v2 if v2 != 0 else 1
        return v1 / float(div_val)

    def iterate_future_bugs(self):
        self._future_bugs += 1

    def get_data_vector(self):
        return {
            'Added/Total': sum(self._added) / float(sum(self._total_loc)),
            'Max Added/Total': self.get_max_ratio(self._added, self._total_loc),
            'Avg Added/Total': self.get_avg_ratio(self._added, self._total_loc),
            'Deleted/Total': sum(self._deleted) / float(sum(self._total_loc)),
            'Max Deleted/Total': self.get_max_ratio(self._deleted, self._total_loc),
            'Avg Deleted/Total': self.get_avg_ratio(self._deleted, self._total_loc),
            'Added/Deleted': self.get_ratio(sum(self._added), sum(self._deleted)),
            'Max Added/Deleted': self.get_max_ratio(self._added, self._deleted),
            'Avg Added/Deleted': self.get_avg_ratio(self._added, self._deleted),
            'bugs': sum(self._bugs),
            'authors': len(self._uniq_authors),
            'start_age': self._start_age,
            'last_touched': self._last_touched,
            'total_touches': len(self._total_loc),
            'future_bugs': (4 if self._future_bugs > 0 else 2)
        }


class Function:

    def __init__(self, name, num_commits, file_path):
        self._name = name
        self._make_delta_list(num_commits)
        self._ranks = []
        self._path = file_path

    def _make_delta_list(self, num_commits):
        self._measure_list = []
        self._added_measure = MeasureList(num_commits, added_vs_total, 'Added/Total LOC')
        self._measure_list.append(self._added_measure)
        self._deleted_measure = MeasureList(num_commits, del_vs_total, 'Del/Total LOC')
        self._measure_list.append(self._deleted_measure)
        self._changed_measure = MeasureList(num_commits, num_change, 'Num Changes')
        self._measure_list.append(self._changed_measure)
        self._added_vs_del = MeasureList(num_commits, added_vs_deleted, 'Added Vs Deleted')
        self._measure_list.append(self._added_vs_del)
        self._bug_fix_measure = MeasureList(num_commits, add_bug_commit, 'Bug Fixes')
        self._measure_list.append(self._bug_fix_measure)

    def iterate_measures(self, commit_diff_num, added_lines, deleted_lines, total, is_bug_fix):
        for measure in self._measure_list:
            measure.iterate_metric(commit_diff_num, added_lines, deleted_lines, total, is_bug_fix)

    def get_added_metric(self):
        return self._added_measure

    def get_deleted_metric(self):
        return self._deleted_measure

    def get_changed_metric(self):
        return self._changed_measure

    def get_added_vs_del_metric(self):
        return self._added_vs_del

    def get_bugfix_metric(self):
        return self._bug_fix_measure

    def __str__(self):
        string = '%s::%s:' % (self._path, self._name)
        for measure in self._measure_list:
            string += '\n\t\t%s: Rank: %s' % (measure.get_name(), measure.get_sum_rank() + 1)
        return string

    def get_dict(self):
        d = {'path': self._path, 'name': self._name, 'measures': []}
        for measure in self._measure_list:
            d['measures'].append({'name': measure.get_name(), 'rank': measure.get_sum_rank() + 1, 'value': measure.get_sum()})
        return d

    def add_rank(self, value):
        self._ranks.append(value)

    def get_rank_sum(self):
        return sum(self._ranks) / float(len(self._ranks))

    def get_sum_rank_avg(self):
        measure_sum_ranks = map(lambda x: x.get_sum_rank(), self._measure_list)
        return sum(measure_sum_ranks) / float(len(measure_sum_ranks))


class ChangedClass:

    def __init__(self, num_commits, path):
        #key this on function name
        self._functions = {}
        self._num_commits = num_commits
        self._path = path

    def add_function_metric(self, func_name, index, added, deleted, total, is_bug_fix):
        if func_name not in self._functions:
            self._functions[func_name] = Function(func_name, self._num_commits, self._path)
        self._functions[func_name].iterate_measures(index, added, deleted, total, is_bug_fix)

    def get_func_count(self):
        return len(self._functions.keys())

    def get_functions(self):
        return self._functions.values()

    def __str__(self):
        string = '%s:' % self._path
        for f in self._functions.values():
            string += '\n\t%s' % str(f)
        return string
