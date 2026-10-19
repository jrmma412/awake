class Awake < Formula
  desc "Keep your Mac awake with the screen on, like caffeinate"
  homepage "https://github.com/jrmma412/awake"
  url "https://github.com/jrmma412/awake.git",
      tag:      "v1.2.1",
      revision: "0f92c5a94fd09e3b53de82e012c610b6d2f78f71"
  license "MIT"
  head "https://github.com/jrmma412/awake.git", branch: "main"

  depends_on :macos

  def install
    bin.install "awake"
  end

  def caveats
    <<~EOS
      Try:  awake 1h
      Optional menu bar icon:  awake menubar
      (uses the separate SwiftBar app; awake asks before installing it)
      Before uninstalling, run:  awake off && awake menubar off
    EOS
  end

  test do
    assert_match version.to_s, shell_output("#{bin}/awake --version")
  end
end
