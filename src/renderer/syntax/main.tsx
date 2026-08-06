import { createRoot } from 'react-dom/client'
import '../common/base.css'
import { SyntaxEditor } from './SyntaxEditor'

createRoot(document.getElementById('root')!).render(<SyntaxEditor />)
