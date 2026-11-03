class Awake < Formula
  desc "Keep your Mac awake with the screen on, like caffeinate"
  homepage "https://github.com/jrmma412/awake"
  url "https://github.com/jrmma412/awake.git",
      tag:      "v1.4.0",
      revision: "0d59c8d6b4905f4ed8b866d7fce703a6994b1603"
  license "MIT"
  head "https://github.com/jrmma412/awake.git", branch: "main"

  depends_on :macos

  def install
    bin.install "awake"
  end

  def caveats
    <<~EOS
      Try:  awake 1h
      Optional menu bar icon:  awake menubar   (hide: awake menubar quit, remove: awake menubar off)
      (uses the separate SwiftBar app; awake asks before installing it)
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
