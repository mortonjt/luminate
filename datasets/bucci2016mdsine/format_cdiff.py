import numpy as np
import pickle as pkl

from util_bucci import write_table

sample_id_to_subject_id = {}
subject_id_time = {}
subject_id_u = {}
subject_id_biomass = {}

f = open("data_cdiff/metadata.txt", "r")
g = open("data_cdiff/biomass.txt", "r")
e = open("cdiff-events.csv", "w")
e.write("ID,eventID,startDay,endDay\n")

for line1, line2 in zip(f, g):
    line1 = line1.split()
    if "sampleID" in line1[0]:
        continue
    sample_id = line1[0]
    subject_id = line1[2]
    day = float(line1[3])
    
    if day == 28.75:
        e.write("{},C. diff,28.75,28.75\n".format(subject_id))

    sample_id_to_subject_id[sample_id] = subject_id
    subject_id_time[subject_id] = subject_id_time.get(subject_id, []) + [day]

    line2 = line2.split()
    line2 = [float(mass) for mass in line2]
    subject_id_biomass[subject_id] = subject_id_biomass.get(subject_id, []) + [np.mean(line2)]
f.close()
g.close()
e.close()

counts = np.loadtxt("data_cdiff/counts.txt", delimiter="\t", dtype=str, comments="!")
otus = counts[:,0]
# remove taxa where counts are mostly 0/1 (no information)
remove_idx = [1, 15, 17, 20, 21, 23]
keep_idx = [ i for i in range(24) if i not in remove_idx ]
remove = counts[remove_idx,1:].astype(float)
counts = counts[keep_idx,1:]
otus = otus[keep_idx][1:]

subject_id_counts = {}

for row in counts.T:
    sample_id = row[0]
    counts = row[1:].astype(float)
    subject_id = sample_id_to_subject_id[sample_id]

    if subject_id in subject_id_counts:
        subject_id_counts[subject_id] = np.vstack( (subject_id_counts[subject_id], np.array(counts)) )
    else:
        subject_id_counts[subject_id] = np.array(counts)

Y_cdiff = []
Y_cdiff_counts = []
T_cdiff = []
IDs_cdiff = []
zero_count = 0
total_count = 0
for subject_id in subject_id_counts:
    y = np.array(subject_id_counts[subject_id])
    t = np.array(subject_id_time[subject_id])

    mass = np.array(subject_id_biomass[subject_id])
    y_mass = y / y.sum(axis=1,keepdims=True)
    y_mass = (y_mass.T * mass/1e9).T
    zero_count += y_mass[y_mass == 0].size
    total_count += y_mass.size
    
    Y_cdiff_counts.append(y)
    Y_cdiff.append(y_mass)
    T_cdiff.append(t)
    IDs_cdiff.append(subject_id)

write_table(IDs_cdiff, Y_cdiff, T_cdiff, otus, "cdiff")
write_table(IDs_cdiff, Y_cdiff_counts, T_cdiff, otus, "cdiff-counts")
#print("% 0", zero_count / total_count)


