import sys
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.core.config import settings
from app.services.llm_manager import LLMManager


@pytest.fixture
def llm_setup(monkeypatch, tmp_path):
    model_file = tmp_path / 'model.gguf'
    model_file.write_bytes(b'GGUF')
    monkeypatch.setattr(settings, 'LLM_MODEL_PATH', str(model_file))
    monkeypatch.setattr(settings, 'LLM_ENABLED', True)
    monkeypatch.setattr(settings, 'LLM_REQUIRE_GPU', True)
    monkeypatch.setattr(settings, 'LLM_N_GPU_LAYERS', -1)
    backend = SimpleNamespace(llama_supports_gpu_offload=lambda: True,
                              Llama=Mock(), LLAMA_SPLIT_MODE_NONE=0)
    monkeypatch.setitem(sys.modules, 'llama_cpp', backend)
    manager = LLMManager()
    monkeypatch.setattr(manager, '_gpu_vram_mb', lambda: {
        'used_mb': 128, 'total_mb': 8192, 'free_mb': 8064, 'name': 'Test GPU',
    })
    return manager, backend


def test_refuses_cpu_backend(llm_setup):
    manager, backend = llm_setup
    backend.llama_supports_gpu_offload = lambda: False
    assert not manager.load_model()
    backend.Llama.assert_not_called()
    assert 'CPU fallback is disabled' in manager._load_error


def test_refuses_partial_offload(llm_setup, monkeypatch):
    manager, backend = llm_setup
    monkeypatch.setattr(settings, 'LLM_N_GPU_LAYERS', 10)
    assert not manager.load_model()
    backend.Llama.assert_not_called()


def test_refuses_insufficient_vram(llm_setup, monkeypatch):
    manager, backend = llm_setup
    monkeypatch.setattr(manager, '_gpu_vram_mb', lambda: {'free_mb': 100})
    assert not manager.load_model()
    backend.Llama.assert_not_called()
    assert 'Insufficient free GPU VRAM' in manager._load_error


def test_gpu_load_and_explicit_release(llm_setup):
    manager, backend = llm_setup
    assert manager.load_model()
    assert manager.load_model()
    backend.Llama.assert_called_once()
    args = backend.Llama.call_args.kwargs
    assert args['n_gpu_layers'] == -1
    assert args['offload_kqv'] is True
    assert args['use_mmap'] is False
    assert manager.unload()['was_loaded'] is True
    backend.Llama.return_value.close.assert_called_once()
    assert not manager.is_loaded()


def test_model_paths_do_not_depend_on_working_directory(tmp_path, monkeypatch):
    from app.core.config import Settings, BACKEND_DIR
    monkeypatch.chdir(tmp_path)
    config = Settings(_env_file=None, LLM_MODEL_PATH='./models/llm/test.gguf')
    assert config.LLM_MODEL_PATH == str(BACKEND_DIR / 'models' / 'llm' / 'test.gguf')
    assert config.PHONEME_VISEME_THRESHOLD == 0.70
