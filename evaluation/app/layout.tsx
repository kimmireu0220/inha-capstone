import type {Metadata} from 'next';
import './globals.css';
export const metadata:Metadata={title:'인물 이미지 평가',description:'인물 이미지 요청 충족·보존·자연스러움 평가'};
export default function Layout({children}:{children:React.ReactNode}){return <html lang="ko"><body>{children}</body></html>}
