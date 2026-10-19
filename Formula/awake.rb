class Awake < Formula
  desc "Keep your Mac awake with the screen on, like caffeinate"
  homepage "https://github.com/jrmma412/awake"
  url "https://github.com/jrmma412/awake.git", branch: "main"
  version "1.2.0"
  license "MIT"

  def install
    bin.install "awake"
  end

  def caveats
    <<~EOS
      Try:  awake 1h
      Optional menu bar icon:  awake menubar
    EOS
  end

  test do
    assert_match "awake", shell_output("#{bin}/awake --version")
  end
end
