{pkgs}: {
  deps = [
    pkgs.playwright-driver
    pkgs.gitFull
    pkgs.glibcLocales
    pkgs.rustc
    pkgs.libiconv
    pkgs.cargo
  ];
}
