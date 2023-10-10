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
def Run(dut, toplevel,
        num_iter=1, template='Template', in_file=None,
        out='output', record=False, cov_log=None,
        multicore=0, manager=None, proc_num=0, start_time=0, start_iter=0, start_cov=0,
        prob_intr=0, no_guide=False, debug=False):

    timestamp_start = time.time()

    record = int(os.environ['IS_RECORD'])

    assert toplevel in ['RocketTile', 'BoomTile' ], \
        '{} is not toplevel'.format(toplevel)

    random.seed(time.time() * (proc_num + 1))

    (mutator, preprocessor, isaHost, rtlHost, checker) = \
        setup(dut, toplevel, template, out, proc_num, debug, no_guide=no_guide)
    timestamp_setup = time.time()
    print('timestamp setup: ', timestamp_setup - timestamp_start)

    if in_file: num_iter = 1

    stop = [ proc_state.NORMAL ]
    mNum = 0
    cNum = 0
    iNum = 0
    last_coverage = 0

    debug_print('[DifuzzRTL] Start Fuzzing', debug)

    if multicore:
        yield manager.cov_restore(dut)

    for it in range(num_iter):
        debug_print('[DifuzzRTL] Iteration [{}]'.format(it), debug)
        timestamp_iter_start = time.time()
        print('absolute time iter start: ', timestamp_iter_start)

        if multicore:
            if it == 0:
                mutator.update_corpus(out + '/corpus', 1000)
            elif it % 1000 == 0:
                mutator.update_corpus(out + '/corpus')

        assert_intr = False
        if random.random() < prob_intr:
            assert_intr = True

        if in_file: (sim_input, data, assert_intr) = mutator.read_siminput(in_file)
        else: (sim_input, data) = mutator.get(assert_intr)

        if debug:
            print('[DifuzzRTL] Fuzz Instructions')
            for inst, INT in zip(sim_input.get_insts(), sim_input.ints + [0]):
                print('{:<50}{:04b}'.format(inst, INT))


        (isa_input, rtl_input, symbols) = preprocessor.process(sim_input, data, assert_intr)

        timestamp_preprocess = time.time()
        print('timestamp preprocess: ', timestamp_preprocess - timestamp_iter_start)


        if isa_input and rtl_input:
            ret = run_isa_test(isaHost, isa_input, stop, out, proc_num)
            timestamp_isa_test = time.time()
            print('timestamp isa test: ', timestamp_isa_test - timestamp_preprocess)
            if ret == proc_state.ERR_ISA_TIMEOUT: continue
            elif ret == proc_state.ERR_ISA_ASSERT: break

            try:
                (ret, coverage) = yield rtlHost.run_test(rtl_input, assert_intr)
                timestamp_rtl_test = time.time()
                print('timestamp rtl test: ', timestamp_rtl_test - timestamp_isa_test)
            except Exception as e:
                print('[DifuzzRTL] RTL Simulation excepted!', flush=True)
                print('[DifuzzRTL] Exception', e, flush=True)
                traceback.print_exc()

                stop[0] = proc_state.ERR_RTL_SIM
                break

            if assert_intr and ret == SUCCESS:
                (intr_prv, epc) = checker.check_intr(symbols)
                if epc != 0:
                    preprocessor.write_isa_intr(isa_input, rtl_input, epc)
                    ret = run_isa_test(isaHost, isa_input, stop, out, proc_num, True)
                    timestamp_second_isa_test = time.time()
                    print('timestamp second isa test: ', timestamp_second_isa_test - timestamp_rtl_test)
                    if ret == proc_state.ERR_ISA_TIMEOUT: continue
                    elif ret == proc_state.ERR_ISA_ASSERT: break
                else: continue

            cause = '-'
            match = False
            if ret == SUCCESS:
                # match = checker.check(symbols)
                match = True # TODO
            elif ret == ILL_MEM:
                match = True
                debug_print('[DifuzzRTL] Memory access outside DRAM -- {}'. \
                            format(iNum), debug, True)
                if record:
                    save_mismatch(out, proc_num, out + '/illegal',
                                  sim_input, data, iNum)
                iNum += 1

            print('[DifuzzRTL] Coverage -- {} [{}]' \
                  .format(coverage, last_coverage), flush=True)

            if not match or ret not in [SUCCESS, ILL_MEM]:
                if multicore:
                    mNum = manager.read_num('mNum')
                    manager.write_num('mNum', mNum + 1)

                if record:
                    save_mismatch(out, proc_num, out + '/mismatch',
                                  sim_input, data, mNum)

                mNum += 1
                if ret == TIME_OUT: cause = 'Timeout'
                elif ret == ASSERTION_FAIL: cause = 'Assertion fail'
                else: cause = 'Mismatch'

                debug_print('[DifuzzRTL] Bug -- {} [{}]'. \
                            format(mNum, cause), debug, not match or (ret != SUCCESS))

            if coverage > last_coverage:
                print('[DifuzzRTL] Incresed coverage')
                if multicore:
                    cNum = manager.read_num('cNum')
                    manager.write_num('cNum', cNum + 1)

                if record:
                    save_file(cov_log, 'a', '{:<10}\t{:<10}\t{:<10}\n'.
                              format(time.time() - start_time, start_iter + it,
                                     start_cov + coverage))
                    sim_input.save(out + '/corpus/id_{}.si'.format(cNum))

                cNum += 1
                mutator.add_corpus(sim_input)
                last_coverage = coverage
            else:
                print('[DifuzzRTL] Coverage not affected')


            if record:
                print('[DifuzzRTL] Saving into illegal (little hack)')
                save_mismatch(out, proc_num, out + '/illegal', sim_input, data, it)

            mutator.update_phase(it)

        else:
            print('[DifuzzRTL] Preprocessing failed!', flush=True)
            stop[0] = proc_state.ERR_COMPILE
            # Compile failed
            break

    if multicore:
        save_err(out, proc_num, manager, stop[0])
        manager.set_state(proc_num, stop[0])

    debug_print('[DifuzzRTL] Stop Fuzzing', debug)

    if multicore:
        yield manager.cov_store(dut, proc_num)
        manager.store_covmap(proc_num, start_time, start_iter, num_iter)
