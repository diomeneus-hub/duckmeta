import tempfile
import unittest
from pathlib import Path
from duckmeta.paths import find_hats_directory, HATS


class PathTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)

    def documents(self, library, profile="steamuser", name="Documents"):
        path = library / "steamapps/compatdata/312530/pfx/drive_c/users" / profile / name
        path.mkdir(parents=True)
        return path

    def test_standard_proton_folder_without_creating_hats(self):
        documents = self.documents(self.home / ".local/share/Steam")
        self.assertEqual(find_hats_directory(self.home,"posix"), documents / HATS)
        self.assertFalse((documents / HATS).exists())

    def test_custom_steam_library_with_spaces(self):
        steam = self.home / ".local/share/Steam"
        (steam / "steamapps").mkdir(parents=True)
        library = self.home / "Games Library"
        documents = self.documents(library)
        (steam / "steamapps/libraryfolders.vdf").write_text('"libraryfolders" { "1" { "path" "'+str(library)+'" "apps" { "312530" "12345" } } }')
        self.assertEqual(find_hats_directory(self.home,"posix"), documents / HATS)

    def test_existing_hats_preferred_over_empty_prefix(self):
        self.documents(self.home / ".local/share/Steam")
        documents = self.documents(self.home / ".steam/steam",name="My Documents")
        (documents / HATS).mkdir(parents=True)
        self.assertEqual(find_hats_directory(self.home,"posix"),documents / HATS)

    def test_flatpak_other_profile_and_legacy_library_file(self):
        root=self.home / ".var/app/com.valvesoftware.Steam/.local/share/Steam"
        (root / "config").mkdir(parents=True)
        library=self.home / "disk"
        documents=self.documents(library,profile="olduser")
        (root / "config/libraryfolders.vdf").write_text('"LibraryFolders" { "1" "'+str(library)+'" }')
        self.assertEqual(find_hats_directory(self.home,"posix"),documents / HATS)

    def test_no_game_does_not_guess_or_create_prefix(self):
        self.assertIsNone(find_hats_directory(self.home,"posix"))
        self.assertEqual(list(self.home.iterdir()),[])

    def test_windows_existing_onedrive_hats_preferred(self):
        (self.home / "Documents").mkdir()
        hats=self.home / "OneDrive/Documents" / HATS
        hats.mkdir(parents=True)
        self.assertEqual(find_hats_directory(self.home,"nt"),hats)
