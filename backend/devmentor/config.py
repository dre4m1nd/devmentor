"""配置：JDK 查找、厂商目录、凭据存储。

对应 Java 版的 MentorProperties / ProviderCatalog / CredentialStore，
但去掉了 Spring 的属性绑定层——直接用 dataclass + 环境变量。
"""

from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

# ---------------------------------------------------------------- 厂商目录


@dataclass(frozen=True, slots=True)
class Provider:
    id: int
    label: str
    provider: str
    env_var: str
    default_base_url: str
    default_model: str
    hint: str
    #: 区分同名 provider 的具体厂商。
    #: openai 前缀同时被 OpenRouter 与 OpenAI 使用（都是 OpenAI 兼容协议），
    #: 光看 provider 分不出来，需要这个字段消歧。
    vendor: str = ""

    def __post_init__(self) -> None:
        if not self.vendor:
            object.__setattr__(self, "vendor", self.provider)


PROVIDERS: list[Provider] = [
    Provider(
        id=1,
        label="OpenRouter（免费模型，推荐）",
        provider="openai",
        env_var="OPENROUTER_API_KEY",
        default_base_url="https://openrouter.ai/api/v1",
        default_model="minimax/minimax-m3.1-flash:free",
        hint="https://openrouter.ai/keys",
        vendor="openrouter",
    ),
    Provider(
        id=2,
        label="DeepSeek",
        provider="deepseek",
        env_var="DEEPSEEK_API_KEY",
        default_base_url="https://api.deepseek.com",
        default_model="deepseek-chat",
        hint="https://platform.deepseek.com/api_keys",
    ),
    Provider(
        id=3,
        label="阿里云百炼 DashScope",
        provider="dashscope",
        env_var="DASHSCOPE_API_KEY",
        default_base_url="",
        default_model="qwen-plus",
        hint="https://bailian.console.aliyun.com/",
    ),
    Provider(
        id=4,
        label="OpenAI",
        provider="openai",
        env_var="OPENAI_API_KEY",
        default_base_url="https://api.openai.com/v1",
        default_model="gpt-4.1-mini",
        hint="https://platform.openai.com/api-keys",
        vendor="openai",
    ),
    Provider(
        id=5,
        label="Anthropic Claude",
        provider="anthropic",
        env_var="ANTHROPIC_API_KEY",
        default_base_url="",
        default_model="claude-sonnet-4-20250514",
        hint="https://console.anthropic.com/settings/keys",
    ),
    Provider(
        id=6,
        label="本地 Ollama（无需 Key）",
        provider="ollama",
        env_var="",
        default_base_url="http://localhost:11434",
        default_model="qwen2.5-coder",
        hint="https://ollama.com/download",
    ),
]


def provider_by_id(pid: int) -> Provider | None:
    return next((p for p in PROVIDERS if p.id == pid), None)


def provider_by_name(name: str | None) -> Provider | None:
    if not name:
        return None
    low = name.lower()
    return next((p for p in PROVIDERS if p.provider == low), None)


def requires_key(p: Provider | None) -> bool:
    return p is not None and bool(p.env_var)


def effective_provider(settings: "Settings", api_key: str | None) -> Provider | None:
    """结合已解析的 api_key 判断真正生效的厂商记录。

    `openai` 前缀同时对应 OpenRouter 与 OpenAI 两条记录（都是 OpenAI 兼容协议）。
    光看 provider 名分不出来，要结合两处信息：
      1. 显式配置的 base_url
      2. key 的前缀（OpenRouter 的 key 以 sk-or- 开头）

    这样即使用户只把 OPENROUTER_API_KEY 写进环境变量、没配 base_url，
    也会正确指向 openrouter 而不是 api.openai.com。
    """
    base = (settings.base_url or "").lower()
    if "openrouter" in base:
        return _by_vendor("openrouter")
    if settings.provider != "openai":
        return provider_by_name(settings.provider)
    if api_key and api_key.startswith("sk-or-"):
        # 明确的 OpenRouter key：不要发到 api.openai.com
        return _by_vendor("openrouter")
    return _by_vendor("openai")


def _by_vendor(vendor: str) -> Provider | None:
    return next((p for p in PROVIDERS if p.vendor == vendor), None)


# ---------------------------------------------------------------- 凭据存储


class CredentialStore:
    """凭据的本地持久化：/login 输入的 Key 落盘到用户目录，下次启动自动读取。

    存储位置 ~/.devmentor/credentials，格式是极简的 provider=key。
    **不加密**——只是放在用户主目录并收紧权限（POSIX 0600）。
    """

    def __init__(self, file: Path | None = None) -> None:
        self._file = file or Path.home() / ".devmentor" / "credentials"

    @property
    def file(self) -> Path:
        return self._file

    def load(self) -> dict[str, str]:
        result: dict[str, str] = {}
        if not self._file.is_file():
            return result
        try:
            text = self._file.read_text(encoding="utf-8")
        except OSError:
            return result
        for line in text.splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            provider, _, key = line.partition("=")
            provider, key = provider.strip().lower(), key.strip()
            if provider and key:
                result[provider] = key
        return result

    def find(self, provider: str | None) -> str | None:
        if not provider:
            return None
        return self.load().get(provider.lower())

    def save(self, provider: str, key: str) -> None:
        data = self.load()
        data[provider.lower()] = key
        self._write(data)

    def remove(self, provider: str) -> None:
        data = self.load()
        if data.pop(provider.lower(), None) is not None:
            self._write(data)

    def _write(self, data: dict[str, str]) -> None:
        self._file.parent.mkdir(parents=True, exist_ok=True)
        lines = [
            "# DevMentor credentials - generated by /login",
            "# 一行一个 provider=key，请勿提交到版本库。",
        ]
        lines += [f"{p}={k}" for p, k in data.items()]
        self._file.write_text("\n".join(lines) + "\n", encoding="utf-8")
        try:
            os.chmod(self._file, 0o600)
        except OSError:
            pass  # Windows 等非 POSIX 文件系统：跳过


# ---------------------------------------------------------------- JDK 查找


def _java_major(java_exe: Path) -> int | None:
    """解析 java -version 的主版本号。

    java 把版本写到 stderr，且不同厂商格式不同（1.8.0_401 / 17.0.2 / 21-ea）。
    """
    try:
        proc = subprocess.run(
            [str(java_exe), "-version"], capture_output=True, text=True, timeout=10
        )
    except (OSError, subprocess.SubprocessError):
        return None
    text = (proc.stderr or "") + (proc.stdout or "")
    for token in text.replace('"', " ").split():
        parts = token.split(".")
        if not parts or not parts[0].isdigit():
            continue
        major = int(parts[0])
        if major == 1 and len(parts) > 1 and parts[1].isdigit():
            return int(parts[1])  # 1.8.0_401 -> 8
        return major
    return None


def _jdk_candidates() -> list[Path]:
    """按优先级返回候选 JDK 目录：显式指定 -> ~/.jdks 扫描 -> JAVA_HOME -> PATH。"""
    out: list[Path] = []

    if explicit := os.environ.get("DEVMENTOR_JAVA_HOME"):
        out.append(Path(explicit))

    jdks = Path.home() / ".jdks"
    if jdks.is_dir():
        # 只认名字里带 17 或更大的，避免对每个子目录都起子进程探测
        import re

        pattern = re.compile(r"^(?:open)?jdk-(17|18|19|2\d|1[89])")
        for child in sorted(jdks.iterdir(), reverse=True):
            if child.is_dir() and pattern.match(child.name):
                out.append(child)

    if java_home := os.environ.get("JAVA_HOME"):
        out.append(Path(java_home))

    return out


def java_executable(need_compiler: bool = False, min_major: int = 17) -> str | None:
    """找一个可用的 JDK 17+ 可执行文件路径。

    need_compiler=True 时要求 javac 存在（编译/运行片段需要，纯 JRE 不行）。
    """
    exe = "javac" if need_compiler else "java"
    for home in _jdk_candidates():
        candidate = home / "bin" / (exe + (".exe" if os.name == "nt" else ""))
        if not candidate.is_file():
            continue
        if need_compiler and not (home / "bin" / ("java" + (".exe" if os.name == "nt" else ""))).is_file():
            continue
        major = _java_major(home / "bin" / ("java" + (".exe" if os.name == "nt" else "")))
        if major is None or major < min_major:
            continue
        return str(candidate)

    # 最后回退到 PATH
    found = shutil.which(exe)
    return found


# ---------------------------------------------------------------- 主配置


@dataclass(slots=True)
class Settings:
    """全部可配置项。所有字段都有安全默认值。"""

    model_id: str = "openai:minimax/minimax-m3.1-flash:free"
    api_key: str = ""
    base_url: str = ""
    language: str = "zh"
    user_id: str = "learner"
    session_id: str = ""
    workspace: Path = field(default_factory=lambda: Path(".devmentor/workspace"))
    state_dir: Path = field(default_factory=lambda: Path(".devmentor/state"))
    project_root: Path | None = None
    permission_mode: str = "interactive"
    max_iters: int = 24
    enable_shell: bool = False
    java_run_timeout: int = 10
    max_source_chars: int = 20000

    @staticmethod
    def from_env() -> "Settings":
        s = Settings()
        s.model_id = os.environ.get("DEVELOPMENT_MODEL_ID", s.model_id)
        s.base_url = os.environ.get("DEVELOPMENT_BASE_URL", s.base_url)
        s.language = os.environ.get("DEVMENTOR_LANGUAGE", s.language)
        s.user_id = os.environ.get("DEVMENTOR_USER_ID", os.environ.get("USER", "learner"))
        if pr := os.environ.get("DEVMENTOR_PROJECT_ROOT"):
            s.project_root = Path(pr)
        if mode := os.environ.get("DEVMENTOR_PERMISSION_MODE"):
            s.permission_mode = mode
        return s

    @property
    def workspace_dir(self) -> Path:
        return self.workspace.resolve()

    @property
    def project_dir(self) -> Path:
        return (self.project_root or Path.cwd()).resolve()

    @property
    def provider(self) -> str:
        return self.model_id.split(":", 1)[0].lower() if ":" in self.model_id else ""

    @property
    def model_name(self) -> str:
        return self.model_id.split(":", 1)[1] if ":" in self.model_id else self.model_id

    def resolve_api_key(self, store: CredentialStore) -> str | None:
        """优先级：环境变量 > 本地凭据文件。

        CI 里注入的 Key 会盖掉开发机 /login 存的个人 Key，
        因此同一台机器跑流水线不会误用个人额度。
        """
        if self.api_key:
            return self.api_key
        for var in self.env_vars():
            value = os.environ.get(var)
            if value:
                return value
        return store.find(self.provider)

    def env_vars(self) -> list[str]:
        """该 provider 可能使用的全部环境变量名。

        注意 openai 前缀可能指向 OpenRouter（其标准变量是 OPENROUTER_API_KEY），
        所以这里返回的是**候选列表**而不是单个名字——按 openai / openrouter
        的 base_url 判断该优先看哪个。
        """
        names: list[str] = []
        base = (self.base_url or "").lower()
        if self.provider == "openai":
            # OpenRouter 也是 openai 兼容协议，但用不同的标准变量名。
            # 显式配了 openrouter 地址时优先它；没配时先看通用变量名，
            # 再退到 OPENROUTER_API_KEY（默认模型就走 OpenRouter 免费模型）。
            if "openrouter" in base:
                names += ["OPENROUTER_API_KEY", "OPENAI_API_KEY"]
            else:
                names += ["OPENAI_API_KEY", "OPENROUTER_API_KEY"]
        else:
            p = provider_by_name(self.provider)
            if p and p.env_var:
                names.append(p.env_var)
        return names

    def provider_env_var(self) -> str:
        """该 provider 的首选环境变量名（用于提示信息）。"""
        vars_ = self.env_vars()
        return vars_[0] if vars_ else ""