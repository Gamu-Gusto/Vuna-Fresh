'use client';

// Shared "your application isn't active yet" screen for both farmers and
// business buyers — same shape of message (pending vs rejected/suspended),
// just different copy/data source per caller.
export default function ApplicationStatusScreen({ status, applicantLabel, reason, email }) {
  const isRejected = status === 'rejected' || status === 'suspended';

  return (
    <div className="max-w-xl mx-auto mt-12 px-4">
      <h1 className="type-display text-5xl">
        {isRejected ? 'Your application wasn’t approved' : 'We’re checking your application'}
      </h1>
      {isRejected ? (
        <>
          <p className="mt-4 text-gray-700 leading-relaxed">
            The Vuna Fresh team didn&apos;t approve your {applicantLabel} application.
          </p>
          {reason && (
            <blockquote className="mt-4 border-l-4 border-ember pl-4 text-gray-800">
              {reason}
            </blockquote>
          )}
          <p className="mt-4 text-gray-700">If you think this is a mistake, reply to the email we sent you.</p>
        </>
      ) : (
        <p className="mt-4 text-gray-700 leading-relaxed">
          Someone from the Vuna Fresh team will look at your {applicantLabel} account, usually within two working
          days. You&apos;ll get full access as soon as it&apos;s approved.
        </p>
      )}
      {email && <p className="mt-8 text-sm text-gray-500">Logged in as {email}</p>}
    </div>
  );
}
