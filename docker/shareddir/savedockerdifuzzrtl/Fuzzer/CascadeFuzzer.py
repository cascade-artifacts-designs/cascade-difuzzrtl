import time
import random
import traceback

from cocotb.decorators import coroutine
from RTLSim.host import ILL_MEM, SUCCESS, TIME_OUT, ASSERTION_FAIL

from src.utils import *
from src.multicore_manager import proc_state

import os
import time


@coroutine
def RunCascade(dut, toplevel,
        num_iter=1, template='Template', in_file=None,
        out='output', record=False, cov_log=None,
        multicore=0, manager=None, proc_num=0, start_time=0, start_iter=0, start_cov=0,
        prob_intr=0, no_guide=False, debug=False):

    timestamp_start = time.time()

    record = int(os.environ['IS_RECORD'])

    assert toplevel in ['RocketTile', 'BoomTile' ], \
        '{} is not toplevel'.format(toplevel)

    random.seed(time.time() * (proc_num + 1))

    rtlHost = rvRTLhost(dut, toplevel, 'DUMMY_SIGFILE', debug=debug)

    timestamp_setup = time.time()
    print('timestamp setup: ', timestamp_setup - timestamp_start)

    if in_file: num_iter = 1

    stop = [ proc_state.NORMAL ]
    mNum = 0
    cNum = 0
    iNum = 0
    last_coverage = 0

    print('[Cascade] Start Fuzzing', debug, flush=True)

    if toplevel == 'RocketTile':
        toplevel_short = 'rocket'
    elif toplevel == 'BoomTile':
        toplevel_short = 'boom'

    # Will remain None and are only here for compatibility with Fuzzer.py
    sim_input = None
    data = None

    for it in range(num_iter):
        curr_file_path = os.path.join('..', 'cascade-elfs', toplevel, 'hex', f"{toplevel_short}_{it}.hex")
        # curr_file_path = os.path.join('..', 'app.hex')

        print('[Cascade] Iteration [{}]'.format(it), debug, flush=True)
        timestamp_iter_start = time.time()
        print('absolute time iter start: ', timestamp_iter_start)

        try:
            (ret, coverage) = yield rtlHost.run_test_cascade(curr_file_path)
            timestamp_rtl_test = time.time()
            print('timestamp rtl test: ', timestamp_rtl_test - timestamp_iter_start)
        except Exception as e:
            print('[Cascade] RTL Simulation excepted!', flush=True)
            print('[Cascade] Exception', e, flush=True)
            traceback.print_exc()

            stop[0] = proc_state.ERR_RTL_SIM
            break

        cause = '-'
        match = False
        if ret == SUCCESS:
            # match = checker.check(symbols)
            match = True # TODO
        elif ret == ILL_MEM:
            match = True
            print('[Cascade] Memory access outside DRAM -- {}'.\
                        format(iNum), flush=True)
            if record:
                save_mismatch(out, proc_num, out + '/illegal',
                                sim_input, data, iNum)
            iNum += 1

        print('[Cascade] Coverage -- {} [{}]' \
                .format(coverage, last_coverage), flush=True)

        if coverage > last_coverage:
            print('[Cascade] Coverage affected')
            last_coverage = coverage
        else:
            print('[Cascade] Coverage not affected')

    print('[Cascade] Stop Fuzzing', debug, flush=True)
