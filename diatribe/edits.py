from dataclasses import dataclass, fields
from abc import ABC, abstractmethod
from pedalboard import Compressor, Chorus, Reverb, Distortion, NoiseGate, Limiter

class AudioEdit(ABC):
    @abstractmethod
    def is_enabled(self) -> bool:
        pass
    @abstractmethod
    def adjustments(self) -> list[str]:
        pass
    
    
class Pedal(ABC):
    @abstractmethod
    def as_pedal(self):
        pass


class EmptyEdit(AudioEdit):
    def is_enabled(self) -> bool:
        return False
    
    def adjustments(self) -> list[str]:
        return []


@dataclass
class ReverbEdit(AudioEdit, Pedal):
    room_size: float = 0.0
    damping: float = 0.0
    wet_level: float = 0.0
    dry_level: float = 0.0
    
    def is_enabled(self) -> bool:
        return self.room_size != 0.0
    
    def adjustments(self) -> list[str]:
        return [f"Reverb:{self.room_size}"]
    
    def as_pedal(self) -> Reverb:
        return Reverb(
            room_size=self.room_size,
            damping=self.damping,
            wet_level=self.wet_level,
            dry_level=self.dry_level
        )
        
@dataclass
class NoiseGateEdit(AudioEdit, Pedal):
    threshold: float = 0.0
    ratio: float = 0.0
    
    def is_enabled(self) -> bool:
        return self.threshold != 0.0
    
    def adjustments(self) -> list[str]:
        return [f"Noise Gate:{self.threshold}dB"]    
    
    def as_pedal(self) -> NoiseGate:
        return NoiseGate(
            threshold_db=self.threshold,
            ratio=self.ratio
        )
        
@dataclass
class LimiterEdit(AudioEdit, Pedal):
    threshold: float = 0.0
    release: float = 0.0
    
    def is_enabled(self) -> bool:
        return self.threshold != 0.0
    
    def adjustments(self) -> list[str]:
        return [f"Limiter:{self.threshold}dB"]
    
    def as_pedal(self) -> Limiter:
        return Limiter(
            threshold_db=self.threshold,
            release_ms=self.release
        )
    
@dataclass
class DistortionEdit(AudioEdit, Pedal):
    drive: float = 0.0
    
    def is_enabled(self) -> bool:
        return self.drive != 0.0
    
    def adjustments(self) -> list[str]:
        return [f"Distortion:{self.drive}dB"]    
    
    def as_pedal(self) -> Distortion:
        return Distortion(
            drive_db=self.drive
        )
        
@dataclass
class CompressorEdit(AudioEdit, Pedal):
    threshold: float = 0.0
    ratio: float = 0.0
    attack: float = 0.0
    release: float = 0.0
    
    def is_enabled(self) -> bool:
        return self.threshold != 0.0
    
    def adjustments(self) -> list[str]:
        return [f"Compressor:{self.threshold}dB"]    
    
    def as_pedal(self) -> Compressor:
        return Compressor(
            threshold_db=self.threshold,
            ratio=self.ratio,
            attack_ms=self.attack,
            release_ms=self.release
        )
        
@dataclass
class ChorusEdit(AudioEdit, Pedal):
    rate: float = 0.0
    depth: float = 0.0
    centre_delay: float = 0.0
    feedback: float = 0.0
    
    def is_enabled(self) -> bool:
        return self.rate != 0.0
    
    def adjustments(self) -> list[str]:
        return [f"Chorus:{self.rate}Hz"]    
    
    def as_pedal(self) -> Chorus:
        return Chorus(
            rate_hz=self.rate,
            depth=self.depth,
            centre_delay_ms=self.centre_delay,
            feedback=self.feedback
        )

@dataclass
class BasicEdit(AudioEdit):
    duration: int = 0
    volume: int = 0
    fade_in: int = 0
    fade_out: int = 0
    trim_in: int = 0
    trim_out: int = 0
    extend_in: int = 0
    extend_out: int = 0
    
    def is_enabled(self) -> bool:
        return any(getattr(self, f.name) != 0 for f in fields(self))
    
    def adjustments(self) -> list[str]:
        a = []
        if self.volume != 0:
            a.append(f"Volume:{self.volume}dB")
        if self.fade_in != 0:
            a.append(f"Fade In:{self.fade_in}ms")
        if self.fade_out != 0:
            a.append(f"Fade Out:{self.fade_out}ms")
        if self.trim_in != 0:
            a.append(f"Trim Start:{self.trim_in}ms")
        if self.trim_out != 0:
            a.append(f"Trim End:{self.trim_out}ms")
        if self.extend_in != 0:
            a.append(f"Extend In:{self.extend_in}ms")
        if self.extend_out != 0:
            a.append(f"Extend Out:{self.extend_out}ms")
        return [f"`{x}`" for x in a]  
    
    def __str__(self) -> str:
        return f"duration: {self.duration}, volume: {self.volume}, fade_in: {self.fade_in}, fade_out: {self.fade_out}, trim_in: {self.trim_in}, trim_out: {self.trim_out}, extend_in: {self.extend_in}, extend_out: {self.extend_out}"

@dataclass
class BackgroundEdit(AudioEdit):
    name: str = None
    fade_in: bool = False
    fade_out: bool = False
    volume: float = 0.0
    
    def is_enabled(self) -> bool:
        return self.name and (self.fade_in or self.fade_out or self.volume != 0.0)
    
    def adjustments(self) -> list[str]:
        return [f"Background:{self.name}"]    
    
@dataclass
class NormalizationEdit(AudioEdit):
    enabled: bool = False
    
    def is_enabled(self) -> bool:
        return self.enabled
    
    def adjustments(self) -> list[str]:
        return ["Audiobook Normalization"]