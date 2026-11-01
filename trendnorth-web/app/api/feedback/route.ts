import { NextResponse } from 'next/server'
import nodemailer from 'nodemailer'

export async function POST(req: Request) {
  try {
    const { name, email, topic, message, honeypot } = await req.json()

    // 1. Honeypot bot trap
    if (honeypot && honeypot.trim().length > 0) {
      return NextResponse.json({ success: true, message: 'Received' })
    }

    // 2. Validation
    if (!name || !email || !message) {
      return NextResponse.json(
        { error: 'Please complete all required fields.' },
        { status: 400 }
      )
    }

    const emailRegex = /^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$/
    if (!emailRegex.test(email.trim())) {
      return NextResponse.json(
        { error: 'Please enter a valid email address.' },
        { status: 400 }
      )
    }

    if (message.trim().split(/\s+/).length < 3) {
      return NextResponse.json(
        { error: 'Please enter at least 3 words describing your feedback.' },
        { status: 400 }
      )
    }

    // 3. Nodemailer SMTP Transporter
    const transporter = nodemailer.createTransport({
      service: 'gmail',
      auth: {
        user: process.env.EMAIL_SENDER,
        pass: process.env.EMAIL_PASSWORD,
      },
    })

    const mailOptions = {
      from: `"TrendNorth Feedback" <${process.env.EMAIL_SENDER}>`,
      to: process.env.EMAIL_RECEIVER || process.env.EMAIL_SENDER,
      subject: `💬 TSX Screener Feedback: [${topic || 'General'}] from ${name.trim()}`,
      html: `
        <div style="font-family: Arial, sans-serif; color: #333; line-height: 1.6; max-width: 600px; padding: 20px; border: 1px solid #e2e8f0; rounded: 8px;">
          <h2 style="color: #0284c7; margin-top: 0;">New User Feedback Received</h2>
          <p><strong>From:</strong> ${name.trim()} (&lt;<a href="mailto:${email.trim()}">${email.trim()}</a>&gt;)</p>
          <p><strong>Topic:</strong> ${topic}</p>
          <p><strong>Timestamp:</strong> ${new Date().toLocaleString('en-US', { timeZone: 'America/New_York' })} ET</p>
          <hr style="border: 0; border-top: 1px solid #e2e8f0; margin: 15px 0;" />
          <p><strong>Feedback Message:</strong></p>
          <blockquote style="background: #f8fafc; border-left: 4px solid #0284c7; padding: 12px 16px; margin: 0; white-space: pre-wrap; font-size: 14px;">
${message.trim()}
          </blockquote>
        </div>
      `,
    }

    await transporter.sendMail(mailOptions)

    return NextResponse.json({ success: true })
  } catch (err: any) {
    console.error('Feedback submission error:', err)
    return NextResponse.json(
      { error: 'Failed to dispatch feedback. Please try again later.' },
      { status: 500 }
    )
  }
}