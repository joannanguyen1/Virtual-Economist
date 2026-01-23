import { Link } from 'react-router-dom'
import '../styles/auth.css'

const SignupPage = () => {
    return (
        <div className='auth-container'>
            <h1>Sign Up</h1>

            <form className='auth-form'>
                <input type="text" placeholder="Full Name" />
                <input type="email" placeholder='Email' />
                <input type="password" placeholder="Password" />
                <button type="submit">Sign Up</button>
            </form>

            <p className='auth-footer'>
                Already have an account? <Link to="/login">Log in</Link>
            </p>

        </div>
    )
}

export default SignupPage