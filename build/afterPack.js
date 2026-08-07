// electron-builder afterPack hook: ad-hoc code-sign the macOS app bundle.
// Apple Silicon refuses to run an arm64 app with no signature at all ("… is
// damaged"). An ad-hoc signature (identity "-") needs no Apple Developer cert
// and makes the app runnable; users still get the normal right-click ▸ Open
// Gatekeeper prompt on first launch (unsigned/unnotarized).
const { execSync } = require('child_process')

exports.default = async function afterPack(context) {
  if (context.electronPlatformName !== 'darwin') return
  const app = `${context.appOutDir}/${context.packager.appInfo.productFilename}.app`
  try {
    execSync(`codesign --deep --force --options runtime --sign - "${app}"`, { stdio: 'inherit' })
    console.log(`[afterPack] ad-hoc signed ${app}`)
  } catch (err) {
    console.warn('[afterPack] ad-hoc sign failed:', err.message)
  }
}
