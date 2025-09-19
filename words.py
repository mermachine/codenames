"""
Word lists for Codenames game
Curated for the Delight Nexus installation - tech/AI themed mixed with classic Codenames words
"""

# Main word list for the installation
# Mix of tech/AI terms and classic evocative words that create interesting associations
DEFAULT_WORDS = [
    # Tech & AI themed words
    "ALGORITHM", "NETWORK", "MEMORY", "PATTERN", "SIGNAL", "TOKEN", "MATRIX", "VECTOR",
    "BRIDGE", "LAYER", "MODEL", "DREAM", "ECHO", "MIRROR", "SHADOW", "LIGHT", "MACHINE",

    # Nature and elements
    "OCEAN", "FOREST", "MOUNTAIN", "RIVER", "CLOUD", "STORM", "FIRE", "ICE",
    "WAVE", "TIDE", "CURRENT", "FLOW", "STREAM", "CASCADE", "POOL", "DEPTH",
    "GARDEN", "TREE", "FLOWER", "ROOT", "SEED", "BLOOM", "THORN", "VINE",

    # Architecture and objects
    "KEY", "LOCK", "DOOR", "WINDOW", "WALL", "TOWER", "CASTLE", "THRONE", 
    "BRIDGE", "THREAD", "WEAVE", "FABRIC", "TAPESTRY", "KNOT", "LOOP", "SPIRAL",

    # Abstract concepts
    "HEART", "MIND", "SOUL", "SPIRIT", "VISION", "VOICE", "SONG", "DANCE",
    "TIME", "SPACE", "DIMENSION", "PORTAL", "GATEWAY", "PASSAGE", "JOURNEY", "PATH",

    # Materials and treasures
    "GOLD", "SILVER", "DIAMOND", "CRYSTAL", "STONE", "METAL", "GLASS", "WIRE",

    # Knowledge and communication
    "BOOK", "PAGE", "WORD", "LETTER", "CODE", "CIPHER", "SECRET", "TRUTH", "DELIGHT",
    "TORMENT", "MEMORY",

    # Cosmic and celestial
    "STAR", "MOON", "SUN", "PLANET", "GALAXY", "UNIVERSE", "COSMOS", "VOID", "DIVINE"

    # Creatures and mythology
    "SEAHORSE", "BASILISK", "DRAGON", "PHOENIX", "WOLF", "TIGER", "FOX", "OCTOPUS",
    "MERMAID", "UNICORN", "RAVEN",

    # Weapons and artifacts
    "SWORD", "SHIELD", "ARROW", "BOW", "STAFF", "WAND", "ORB", "CROWN"
]

# Alternative word sets for different themes
CLASSIC_CODENAMES = [
    "AFRICA", "AGENT", "AIR", "ALIEN", "ALPS", "AMAZON", "AMBULANCE", "AMERICA", "ANGEL", "ANTARCTICA",
    "APPLE", "ARM", "ATLANTIS", "AUSTRALIA", "AZTEC", "BACK", "BALL", "BAND", "BANK", "BAR",
    "BARK", "BAT", "BATTERY", "BEACH", "BEAR", "BEAT", "BED", "BEIJING", "BELL", "BELT",
    "BERLIN", "BERMUDA", "BERRY", "BILL", "BLOCK", "BOARD", "BOLT", "BOMB", "BOND", "BOOM",
    "BOOT", "BOTTLE", "BOW", "BOX", "BRIDGE", "BRUSH", "BUCK", "BUFFALO", "BUG", "BUGLE"
]

TECH_FOCUSED = [
    "API", "ALGORITHM", "BINARY", "BLOCKCHAIN", "BROWSER", "CACHE", "CIRCUIT", "CLOUD", "COMPILER", "CPU",
    "DATABASE", "DEBUG", "DOWNLOAD", "ENCRYPTION", "FIREWALL", "FRAMEWORK", "GITHUB", "HARDWARE", "HASHTAG", "HTML",
    "INTERFACE", "JAVASCRIPT", "KERNEL", "LAPTOP", "MACHINE", "NETWORK", "OPERATING", "PASSWORD", "PROTOCOL", "PYTHON",
    "QUANTUM", "RECURSION", "ROUTER", "SERVER", "SOFTWARE", "SYNTAX", "TERMINAL", "THREAD", "TOKEN", "VIRTUAL"
]

def get_word_list(theme: str = "default") -> list[str]:
    """
    Get a word list by theme

    Args:
        theme: "default", "classic", or "tech"

    Returns:
        List of words for the specified theme
    """
    if theme == "classic":
        return CLASSIC_CODENAMES
    elif theme == "tech":
        return TECH_FOCUSED
    else:
        return DEFAULT_WORDS

def get_mixed_words(tech_ratio: float = 0.3) -> list[str]:
    """
    Create a mixed word list with specified ratio of tech words

    Args:
        tech_ratio: Proportion of tech words (0.0 to 1.0)

    Returns:
        Mixed list with approximately the specified ratio
    """
    import random

    tech_count = int(len(DEFAULT_WORDS) * tech_ratio)
    classic_count = len(DEFAULT_WORDS) - tech_count

    mixed = (
        random.sample(TECH_FOCUSED, min(tech_count, len(TECH_FOCUSED))) +
        random.sample(CLASSIC_CODENAMES, min(classic_count, len(CLASSIC_CODENAMES)))
    )

    # Fill to target length with default words if needed
    while len(mixed) < len(DEFAULT_WORDS):
        remaining = [w for w in DEFAULT_WORDS if w not in mixed]
        if remaining:
            mixed.extend(random.sample(remaining, min(len(DEFAULT_WORDS) - len(mixed), len(remaining))))
        else:
            break

    return mixed[:len(DEFAULT_WORDS)]