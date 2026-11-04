class Awake < Formula
  desc "Keep your Mac awake with the screen on, like caffeinate"
  homepage "https://github.com/jrmma412/awake"
  url "https://github.com/jrmma412/awake.git",
      tag:      "v1.6.1",
      revision: "8c431a9b87d704b82916566693c030f814c7bbb3"
  license "MIT"
  head "https://github.com/jrmma412/awake.git", branch: "main"

  depends_on :macos

  def install
    bin.install "awake"
  end

  def caveats
    <<~EOS
      Try:  awake 1h   or   awake until 5pm
      Optional menu bar icon:  awake menubar   (hide: awake menubar quit, remove: awake menubar off)
      (uses the separate SwiftBar app; awake asks before installing it)
      Everything at once (keep awake + jiggle + agent):  awake all   (stop: awake all off)
      Optional mouse jiggle (needs Accessibility permission):  awake jiggle 2h   (stop: awake jiggle off)
      Optional always-on mode for agents/servers (display still sleeps and locks):  awake agent
      To remove everything later:  awake uninstall --all
      (or run `awake off` before `brew uninstall awake`)
    EOS
  end

  test do
    assert_match version.to_s, shell_output("#{bin}/awake --version")
  end
end
