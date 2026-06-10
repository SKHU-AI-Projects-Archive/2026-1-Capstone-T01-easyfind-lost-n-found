import multiprocessing as mp
import argparse
import shutil
from datetime import datetime, timedelta
from pathlib import Path

from core.streamer import SourceStreamer
from core.executor import PipelineExecutor
from core.aggregator import OutputAggregator
from core.latest_slot import LatestSlot
from core.utils.config_loader import load_config


def cleanup_stale_shm(config):
    """이전 실행에서 정리되지 않은 SharedMemory 세그먼트를 시작 전에 해제한다.
    (프로세스가 강제 종료되면 Windows/POSIX 모두 세그먼트가 잔존할 수 있다.)"""
    from multiprocessing import shared_memory
    for s in config.get('sources', []):
        name = s.get('shared_memory_name')
        if not name:
            continue
        try:
            shm = shared_memory.SharedMemory(name=name, create=False)
            shm.close()
            shm.unlink()
            print(f"[Cleanup] Released stale SharedMemory '{name}'")
        except FileNotFoundError:
            pass
        except Exception:
            pass


def cleanup_abandoned_files(days=10):
    cutoff = datetime.now() - timedelta(days=days)
    data = Path(__file__).parent / 'data'

    for folder_name in ('scenes', 'logs', 'obj-imgs'):
        base = data / folder_name
        if not base.exists():
            continue
        for pipename_dir in base.iterdir():
            if not pipename_dir.is_dir():
                continue
            for date_dir in pipename_dir.iterdir():
                if not date_dir.is_dir():
                    continue
                try:
                    parts = date_dir.name.split('-')
                    date = datetime(int(parts[0]), int(parts[1]), int(parts[2]))
                    if date < cutoff:
                        shutil.rmtree(date_dir)
                        print(f"[Cleanup] Removed {date_dir}")
                except (ValueError, IndexError):
                    continue


if __name__ == "__main__":
    mp.set_start_method("spawn")
    cleanup_abandoned_files(days=7)
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config", type=str, default="configs/multi_cam.yaml")
    args = parser.parse_args()

    config = load_config(args.config)
    cleanup_stale_shm(config)  # 이전 실행 잔존 SharedMemory 정리

    print(f">>> Multi-Source System (Separate Windows) Initialize.")

    result_queue = mp.Queue()
    processes = []
    multi_pipe_queues = {}

    # 검색 파이프라인(archive_source)이 있으면 제어 핸들 생성
    arch_src = next((s for s in config.get('sources', []) if s.get('type') == 'ArchiveSource'), None)
    if arch_src is not None:
        search_ctrl = {'job_q': mp.Queue(), 'pause': mp.Event(), 'stop': mp.Event()}
        search_ctx = {**search_ctrl,
                      'root': arch_src.get('root', 'archives'),
                      'thumb_root': config.get('search', {}).get('thumb_root', 'search_results')}
    else:
        search_ctrl, search_ctx = None, None

    # 1. Pipelines
    for pipe_conf in config.get('pipelines', []):
        if not pipe_conf.get('enable', True): 
            continue
        
        src_id = pipe_conf.get('source_id')
        src_meta = next((s for s in config.get('sources', []) if s['id'] == src_id), None)
        if not src_meta: 
            print(f"Warning: Source ID '{src_id}' not found for pipeline '{pipe_conf.get('name')}'")
            continue
        
        shm_name = src_meta['shared_memory_name']
        p_in_q = LatestSlot()
        if src_id not in multi_pipe_queues: 
            multi_pipe_queues[src_id] = []
        multi_pipe_queues[src_id].append(p_in_q)

        executor = PipelineExecutor(pipe_conf, p_in_q, result_queue, shm_name)
        executor.start()
        processes.append(executor)

    # 2. Aggregator (검색 제어 컨텍스트를 WebHandler에 주입)
    aggregator = OutputAggregator(config.get('output', {}), result_queue, search_ctx)
    aggregator.start()
    processes.append(aggregator)

    # 3. Streamers (archive_source면 검색 제어 핸들 주입 → detector가 검색 요청 시 구동)
    for src_conf in config.get('sources', []):
        src_id = src_conf['id']
        shm_name = src_conf['shared_memory_name']
        queues = multi_pipe_queues.get(src_id, [])
        if not queues:
            print(f"Info: No active pipelines for source '{src_id}'. Skipping streamer.")
            continue

        ctrl = search_ctrl if src_conf.get('type') == 'ArchiveSource' else None
        streamer = SourceStreamer(src_conf, shm_name, queues, source_ctrl=ctrl)
        streamer.start()
        processes.append(streamer)

    print(">>> All processes started. Each pipeline will have its own window.")

    try:
        aggregator.join()
    except KeyboardInterrupt:
        print("\n>>> Keyboard Interrupt.")
    finally:
        print(">>> Shutting down...")
        for p in processes:
            if hasattr(p, 'stop'):
                p.stop()
        # PipelineExecutor의 blocking get()이 종료 신호를 받을 수 있도록 None 센티널 전송
        for queues in multi_pipe_queues.values():
            for q in queues:
                try:
                    q.put(None)
                except Exception:
                    pass
        # archive_source의 job_q.get() blocking 해제
        if search_ctrl is not None:
            try:
                search_ctrl['stop'].set()
                search_ctrl['job_q'].put(None)
            except Exception:
                pass
        for p in processes:
            p.terminate()
            p.join()
        print(">>> Shutdown complete.")
