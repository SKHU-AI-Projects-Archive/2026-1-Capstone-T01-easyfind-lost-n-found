import multiprocessing as mp
import yaml
import argparse

from core.sources import SourceStreamer
from core.pipelines import PipelineExecutor
from core.outputs import OutputAggregator

if __name__ == "__main__":
    mp.set_start_method("spawn")

    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config", type=str, default="configs/dummy_config.yaml")
    args = parser.parse_args()

    with open(args.config, 'r') as f:
        config = yaml.safe_load(f)

    SHM_NAME = config.get('setting', {}).get('shared_memory_name', "exp_dummy")

    print(f">>> System Initialize. SHM: {SHM_NAME}")

    pipe_queues = []
    result_queue = mp.Queue()
    processes = []

    for pipe_conf in config.get('pipelines', []):
        if not pipe_conf.get('enable', False):
            continue

        p_in_q = mp.Queue()
        pipe_queues.append(p_in_q)

        executor = PipelineExecutor(
            config=pipe_conf,
            input_queue=p_in_q,
            result_queue=result_queue,
            shm_name=SHM_NAME
        )
        executor.start()
        processes.append(executor)

    aggregator = OutputAggregator(
        config=config.get('output', {}),
        result_queue=result_queue,
        shm_name=SHM_NAME
    )
    aggregator.start()
    processes.append(aggregator)

    source_streamer = SourceStreamer(
        config=config.get('source', {}),
        shm_name=SHM_NAME,
        queues=pipe_queues
    )
    source_streamer.start()
    processes.append(source_streamer)

    print(">>> All processes started. Press 'q' in the visualizer window to quit.")

    try:
        aggregator.join()
    except KeyboardInterrupt:
        print("\n>>> Keyboard Interrupt detected.")
    finally:
        print(">>> Stopping processes...")
        source_streamer.stop()
        for p in processes:
            if hasattr(p, 'stop'):
                p.stop()
            p.terminate()
            p.join()
        print(">>> Shutdown complete.")
