class Awake < Formula
  desc "Keep your Mac awake with the screen on, like caffeinate"
  homepage "https://github.com/jrmma412/awake"
  url "https://github.com/jrmma412/awake.git",
      tag:      "v1.2.3",
      revision: "238da9d9f4c02c8a2578548a9145d729dc00470d"
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
      To remove everything later:  awake uninstall --all
    EOS
  end

  test do
    assert_match version.to_s, shell_output("#{bin}/awake --version")
  end
end
