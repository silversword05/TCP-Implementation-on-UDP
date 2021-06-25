from typing import List

from matplotlib import pyplot as plt

FILE_NAME = 'cwnd_data.log'
with open(FILE_NAME, 'r') as f_in:
    data: List[str] = f_in.readlines()
    data: List[str] = [x.strip(' \n') for x in data]

initial_time = float(data[0].split(' ')[1])
data_time, data_cwnd, data_ssthresh = [], [], []

for line in data:
    tokens: List[str] = line.split(' ')
    data_time.append(float(tokens[1]) - initial_time)
    data_cwnd.append(float(tokens[5]))
    data_ssthresh.append(float(tokens[7]))

window_size = 5
ignore_initial_data_points = 100


def moving_average(numbers: List):
    moving_averages = []
    i = 0
    while i < len(numbers) - window_size + 1:
        this_window = numbers[i: i + window_size]
        window_average = sum(this_window) / window_size
        moving_averages.append(window_average)
        i += 1
    return moving_averages


data_time = moving_average(data_time[ignore_initial_data_points:])
data_cwnd = moving_average(data_cwnd[ignore_initial_data_points:])
data_ssthresh = moving_average(data_ssthresh[ignore_initial_data_points:])

plt.plot(data_time, data_cwnd, label='cwnd', c='r')
plt.plot(data_time, data_ssthresh, label='ssthresh', c='b')
plt.xlabel('Time Diff from initial in seconds', fontsize=25)
plt.ylabel('cwnd/ssthresh in MSS', fontsize=25)
plt.legend(fontsize = 25)
plt.show()
