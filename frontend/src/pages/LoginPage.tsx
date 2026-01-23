import { Link } from 'react-router-dom'
import '../styles/auth.css'

const LoginPage = () => {
    return (
        <div className='auth-container'>
            <h1>Log In</h1>

            <form className='auth-form'>
                <input type="email" placeholder='Email' />
                <input type="password" placeholder='Password'/>

                <button type = "submit">Log In</button>
            </form>

            <p className="auth-footer">
                Don't have an account? <Link to="/signup">Sign up</Link>
            </p>
        </div>
    )
}

export default LoginPage