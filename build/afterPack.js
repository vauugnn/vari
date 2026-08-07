// electron-builder afterPack hook (macOS).
//
// - No signing cert (CSC_LINK unset): ad-hoc sign the whole bundle so Apple
//   Silicon will run it ("… is damaged" otherwise). Still shows the Gatekeeper
//   right-click ▸ Open prompt.
// - Signing cert present: deep-sign the bundled PyInstaller sidecar (its many
//   .so/.dylib/executables) with the Developer ID + hardened runtime, so
//   electron-builder's outer signature and notarization pass. electron-builder
//   signs the Electron parts itself afterward.
const { execSync } = require('child_process')
const path = require('path')

exports.default = async function afterPack(context) {
  if (context.electronPlatformName !== 'darwin') return
  const app = path.join(context.appOutDir, `${context.packager.appInfo.productFilename}.app`)
  const sidecar = path.join(app, 'Contents', 'Resources', 'sidecar-bin')
  const hasCert = !!process.env.CSC_LINK
  const ent = path.join(process.cwd(), 'build', 'entitlements.mac.plist')

  try {
    if (hasCert) {
      const id = 'Developer ID Application'
      // Sign every Mach-O inside the frozen sidecar (leaves first).
      execSync(
        `find "${sidecar}" -type f \\( -name '*.so' -o -name '*.dylib' -o -name '*.framework' -o -perm +111 \\) ` +
          `-print0 | xargs -0 -I{} codesign --force --timestamp --options runtime --entitlements "${ent}" -s "${id}" "{}"`,
        { stdio: 'inherit', shell: '/bin/bash' }
      )
      console.log('[afterPack] Developer ID-signed sidecar binaries')
    } else {
      execSync(`codesign --deep --force --options runtime --sign - "${app}"`, { stdio: 'inherit' })
      console.log('[afterPack] ad-hoc signed', app)
    }
  } catch (err) {
    console.warn('[afterPack] signing step failed:', err.message)
  }
}
