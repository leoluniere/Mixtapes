fn main() {
    // Embed icon into the launcher exe
    if std::path::Path::new("launcher.rc").exists() {
        embed_resource::compile("launcher.rc", embed_resource::NONE);
    }

    // Make the launcher a Windows GUI app (no console window)
    // Only for the Mixtapes binary, not MixtapesBridge (which needs stdin/stdout)
    let target = std::env::var("CARGO_BIN_NAME").unwrap_or_default();
    if target == "Mixtapes" {
        println!("cargo:rustc-link-arg-bin=Mixtapes=-mwindows");
    }
}
