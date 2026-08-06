import { createRoot } from 'react-dom/client'
import '../common/base.css'
import { Viewer } from './Viewer'

createRoot(document.getElementById('root')!).render(<Viewer />)
