# Helper functions to save a load data.

import os
import sys
import numpy as np
import scipy.misc

def parse_otu_table(filename, sep=",", has_rownames=True):
    """Reads an OTU table of multiple time-series observations. Each
    row is an OTU, and each column is an observation from a single
    time point.
    
    Specifically, the format of the OTU table is:
        Row 1: Unique identifiers per sequence. For example, if
               there are 30 observed sequences, these could be labeled
               from 1, 2,.., 30.
        Row 2: Integers specifying the time-point of each observation.
               For example, if observations are in days, one row could
               look like: 3  5  10 ... .
        Row N: The remaining rows are counts of each OTU across all
               observed sequences and time points.
    
    Together, rows 1 and 2 uniquely identify a time point. For instance,
    the column corresponding to observed sequence 7 at time point 3 should
    have 7 in the first row and 3 in the second row.

    Parameters
    ----------
        filename     : a string denoting the filepath of the OTU table.
        sep          : character denoting separator between observations.
        has_rownames : if True, the first column is ignored

    Returns
    -------
        seq_id       : a numpy array of ids identifying each sequence in the
                       otu_table
        otu_table    : a numpy array of observations. The format is the same
                       as the original otu table
    """
    #print("Parsing OTU table...")

    with open(filename, "r") as f:
        lines = f.readlines()
        n_row = len(lines[1:])

        if has_rownames:
            #print("\tSkipping first column as row names.", file=sys.stderr)
            n_col = len(lines[0].split(sep)) - 1
            seq_id = np.array(lines[0].strip("\n").split(sep))[1:]
        else:
            n_col = len(lines[0].split(sep))
            seq_id = np.array(lines[0].strip("\n").split(sep))

        table = np.zeros((n_row, n_col))

        for idx, line in enumerate(lines[1:]):
            if has_rownames:
                line = line.strip("\n").split(sep)[1:]
            else:
                line = line.strip("\n").split(sep)
            n_col_line = len(line)

            if n_col_line != n_col:
                print_error_and_die("Error parsing OTU table: row " + str(idx) + \
                                    " has " + str(n_col_line) + " columns, but row 0 has" + \
                                    n_col + " columns.")

            try:
                row = np.array(line, dtype=float)
            except ValueError:
                print_error_and_die("Error parsing OTU table: invalid character in row " + str(idx))

            if idx > 1 and np.any(row < 0.):
                print_error_and_die("Error parsing OTU table: row " + str(idx) + " has negative entry.")

            if row.sum() == 0:
                print("\tWarning: row " + str(idx) + " has no nonzero entries.", file=sys.stderr)

            table[idx] = row

        return seq_id, table


def parse_event_table(filename, sep=",", has_header=True):
    """Reads a table of external events; for example antibiotic
       administration over a number of days.
    
    The format of the event table is assumed to have four columns:
        Column 1: Unique ID of the corresponding time series observation
        Column 2: Integer ID corresponding to a particular event.
        Column 3: Time point corresponding to the start of the event. This
                  must be greater than or equal to the time point of the first
                  time series observation.
        Column 4: Time point corresponding to the end of the event. This should be
                  less than or equal to the last time series observation.
        Column 5: Optional. Magnitude of the event.

    Parameters
    ----------
        sep       : delimiter used to denote separation between columns
        has_header: if True, the first row is ignored.

    Returns
    -------
        events       : a numpy array of (event_integer_id, start_day, end_day)
                       for each event in filename
        event_to_int : a dictionary that maps event names to unique integers
        seq_id       : sequence id of each row in events
    """
    #print("Parsing event table...", file=sys.stderr)
    # if has_header:
    #     print("\tSkipping first row as header.", file=sys.stderr)

    with open(filename, "r") as f:
        lines = f.readlines()
        if has_header:
            lines = lines[1:]

        n_col = len(lines[0].strip("\n").split(sep))
        n_row = len(lines)

        event_types = []
        # parse to find all event types and check formatting
        for idx, line in enumerate(lines):
            if has_header:
                row_num = idx + 1
            else:
                row_num = idx

            line = line.strip("\n").split(sep)
            if len(line) != n_col:
                print_error_and_die("Error parsing event table: row " + str(row_num) + " has " + \
                                    str(len(line)) + " columns, but header has " + str(n_col) + ".")

            try:
                start_day = float(line[2])
                end_day = float(line[3])
            except ValueError:
                print_error_and_die("Error parsing event table: row " + str(row_num) + " has an invalid entry for start day or end day.")

            if line[1] not in event_types:
                event_types.append(line[1])

        # store events in numpy array
        event_to_int = dict( [(event, i) for i, event in enumerate(event_types) ])
        seq_id = []
        events = np.zeros((n_row, 4))

        for idx, line in enumerate(lines):
            line = line.strip("\n").split(sep)
            seq_id.append(line[0])
            e_idx = event_to_int[line[1]]
            start_day = float(line[2])
            end_day = float(line[3])
            e_size = float(line[4]) if len(line) > 4 else 1
            row = np.array((e_idx, start_day, end_day, e_size))
            events[idx] = row

        return events, event_to_int, seq_id, event_types


def format_observations(otu_table,
                        otu_seq_id,
                        event_table,
                        event_seq_id,
                        event_to_int):
    # counts
    Y = []
    # effects
    U = []
    # times
    T = []

    sort_by_seq = np.argsort(otu_seq_id)
    IDs = np.unique(otu_seq_id)
    otu_table = otu_table[:,sort_by_seq]
    otu_seq_id = otu_seq_id[sort_by_seq]
    for s_id in np.unique(otu_seq_id):
        seq = otu_table[:,np.array(otu_seq_id) == s_id]
        sort_by_day = np.argsort(seq[0])
        seq = seq[:,sort_by_day]
        days = np.array(seq[0], dtype=float)

        if days.size <= 1:
            print("\tWarning: observation {} has only 1 time point".format(s_id), file=sys.stderr)

        observations = []
        for day in days:
            idx = np.argwhere(days == day)
            idx = idx.reshape(idx.size)
            row = seq[1:,idx]
            if (row.shape[1] > 1):
                print("\tWarning: sequence id " + s_id + " has multiple observations for time point " + str(day), file=sys.stderr)
                row = row[:,0]
            row = row.reshape(row.size)
            observations.append(row)

        if event_table is not None:
            effects = np.zeros((len(days), len(event_to_int.values())))
            events = event_table[np.array(event_seq_id) == s_id,:]

            for event in events:
                event_idx = int(event[0])
                start_day = event[1]
                end_day = event[2]
                event_size = event[3]

                for day_idx, day in enumerate(days[:-1]):
                    # # day \in [start_day, end_day)
                    # if start_day <= day and day < end_day and end_day >= days[day_idx+1]:
                    #     effects[day_idx] = event_size*(days[day_idx+1] - day)
                    # # day == end_day (include end point)
                    # elif day == end_day:
                    #     effects[day_idx] = event_size
                    if day >= start_day and day <= end_day:
                        effects[day_idx, event_idx] = event_size
                    elif start_day >= day and end_day <= days[day_idx+1] and start_day < days[day_idx+1]:
                        effects[day_idx, event_idx] = event_size

                effects[-1,event_idx] = event_size if start_day == days[-1] else 0

        else:
            effects = np.zeros((len(days), 1))

        Y.append(np.array(observations))
        U.append(effects)
        T.append(days)

    return IDs, Y, U, T


def load_observations(otu_filename, event_filename = ""):
    """Read observations and transform to use with PoissonLDS.
    
    Parameters
    ----------
        otu_filename   : filepath of otu table
        event_filename : filepath of event table
    """

    otu_seq_id, otu_table = parse_otu_table(otu_filename, 
                                        sep=",",
                                        has_rownames=True)

    if event_filename != "":
        events, event_to_int, event_seq_id, event_names = parse_event_table(event_filename, sep=",")
    else:
        events = None
        event_seq_id = None
        event_to_int = None
        event_names = None

    # U list of length number of patients
    # U[i] is a matrix of t_pts by effects
    IDs, Y, U, T = format_observations(otu_table, otu_seq_id, events, event_seq_id, event_to_int)
    
    return IDs, Y, U, T, event_names



def print_error_and_die(error_msg):
    """Prints error_msg to stderr and halts program.
    """
    print(error_msg, file=sys.stderr)
    exit(1)



def write_table(IDs, Y_pred, T, otu_table, output_dir, postfix):
    predictions = {}
    p_idx = 0
    for p_id, y_pred, days in zip(IDs, Y_pred, T):
        for t,day in enumerate(days):
            predictions[(str(p_id),str(day))] = y_pred[t]

    in_table = np.loadtxt(otu_table, delimiter=",", dtype=str)
    out_table = np.zeros(in_table.shape)

    for j,col in enumerate(in_table[:,1:].T):
        p_id = col[0]
        day = str(float(col[1]))

        out_table[2:,j+1] = predictions[(p_id, day)]

    out_table      = out_table.astype(str)
    out_table[0]   = in_table[0]
    out_table[1]   = in_table[1]
    out_table[:,0] = in_table[:,0]
    basename = os.path.basename(otu_table)
    filename = ".".join(basename.split(".")[:-1]) + "-{}.csv".format(postfix)
    np.savetxt(output_dir + "/" + filename, out_table, delimiter=",", fmt="%s")